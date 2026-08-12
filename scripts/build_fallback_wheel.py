#!/usr/bin/env python3
"""Build the universal fallback wheel from the root canonical metadata."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def _record_hash(payload: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest())
    return "sha256=" + digest.rstrip(b"=").decode("ascii")


def normalize_static_metadata(wheel: Path) -> None:
    """Remove setuptools' derived-only Dynamic marker and rebuild RECORD."""
    with zipfile.ZipFile(wheel) as archive:
        infos = archive.infolist()
        payloads = {info.filename: archive.read(info.filename) for info in infos}

    metadata_names = [
        name for name in payloads if name.endswith(".dist-info/METADATA")
    ]
    record_names = [name for name in payloads if name.endswith(".dist-info/RECORD")]
    if len(metadata_names) != 1 or len(record_names) != 1:
        raise SystemExit("fallback wheel has invalid dist-info layout")

    metadata_name = metadata_names[0]
    metadata = payloads[metadata_name].decode("utf-8")
    lines = metadata.splitlines(keepends=True)
    removed = [line.strip() for line in lines if line.startswith("Dynamic:")]
    if removed != ["Dynamic: license-file"]:
        raise SystemExit("unexpected setuptools Dynamic fields: %r" % removed)
    payloads[metadata_name] = "".join(
        line for line in lines if not line.startswith("Dynamic:")
    ).encode("utf-8")

    record_name = record_names[0]
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for info in infos:
        name = info.filename
        if name == record_name:
            continue
        payload = payloads[name]
        writer.writerow((name, _record_hash(payload), str(len(payload))))
    writer.writerow((record_name, "", ""))
    payloads[record_name] = output.getvalue().encode("utf-8")

    normalized = wheel.with_suffix(".normalized.whl")
    with zipfile.ZipFile(normalized, "w") as archive:
        for info in infos:
            archive.writestr(info, payloads[info.filename])
    normalized.replace(wheel)


def canonical_fallback_pyproject() -> str:
    source = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_start = source.index("[project]\n")
    tools_start = source.index("[tool.maturin]\n")
    project_metadata = source[project_start:tools_start].rstrip()
    return "\n".join(
        (
            "[build-system]",
            'requires = ["setuptools>=77", "wheel"]',
            'build-backend = "setuptools.build_meta"',
            "",
            project_metadata,
            "",
            "[tool.setuptools]",
            'py-modules = ["rfc3339_validator"]',
            "",
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="fast-rfc3339-fallback-build-") as tmp:
        staging = Path(tmp)
        (staging / "pyproject.toml").write_text(
            canonical_fallback_pyproject(), encoding="utf-8"
        )
        (staging / "setup.cfg").write_text(
            "[bdist_wheel]\nuniversal = 1\n", encoding="utf-8"
        )
        for relative in ("README.md", "LICENSE"):
            shutil.copy2(ROOT / relative, staging / relative)
        shutil.copy2(
            ROOT / "fallback" / "rfc3339_validator.py",
            staging / "rfc3339_validator.py",
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "--outdir",
                str(output),
            ],
            cwd=staging,
            check=True,
        )

    wheels = sorted(output.glob("*-py2.py3-none-any.whl"))
    if len(wheels) != 1:
        raise SystemExit("expected one universal fallback wheel, found: {}".format(wheels))
    normalize_static_metadata(wheels[0])
    print(wheels[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

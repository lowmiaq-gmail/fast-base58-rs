#!/usr/bin/env python3
"""Audit the immutable native/fallback release set and canonical metadata."""

from __future__ import annotations

import argparse
import base64
import csv
import email.parser
import hashlib
import io
import pathlib
import tarfile
import zipfile

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet


EXPECTED_NAME = "fast-rfc3339-validator-rs"
EXPECTED_VERSION = "0.1.0"
EXPECTED_REQUIRES_PYTHON = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*"
EXPECTED_REQUIRES_DIST = {
    ("six", "", ""),
    ("pytest", "<9,>=8", 'extra == "test"'),
    ("hypothesis", ">=6", 'extra == "test"'),
    ("strict-rfc3339", "==0.7", 'extra == "test"'),
}
EXPECTED_SUMMARY = "Fast Rust-backed drop-in replacement for rfc3339-validator 0.1.4"
EXPECTED_AUTHOR = "fast-rfc3339-validator-rs contributors"
EXPECTED_LICENSE = "MIT"
EXPECTED_KEYWORDS = (
    "rfc3339",
    "rfc3339-validator",
    "validation",
    "datetime",
    "pyo3",
    "rust",
    "drop-in-replacement",
)
EXPECTED_CLASSIFIERS = {
    "Development Status :: 3 - Alpha",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Rust",
    "Topic :: Software Development :: Libraries :: Python Modules",
}
EXPECTED_PROJECT_URLS = {
    (
        "Changelog",
        "https://github.com/lowmiaq-gmail/fast-rfc3339-validator-rs/blob/main/CHANGELOG.md",
    ),
    ("Homepage", "https://github.com/lowmiaq-gmail/fast-rfc3339-validator-rs"),
    ("Issues", "https://github.com/lowmiaq-gmail/fast-rfc3339-validator-rs/issues"),
    ("Repository", "https://github.com/lowmiaq-gmail/fast-rfc3339-validator-rs"),
}
TEXT_SUFFIXES = (".py", ".json", ".txt", ".md", ".toml")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=pathlib.Path, required=True)
    parser.add_argument("--repository-root", type=pathlib.Path, required=True)
    parser.add_argument("--expected-native-wheels", type=int, required=True)
    return parser.parse_args()


def assert_safe_paths(names):
    for name in names:
        path = pathlib.PurePosixPath(name)
        assert not path.is_absolute(), name
        assert ".." not in path.parts, name


def canonical_requirements(values):
    result = set()
    for value in values:
        requirement = Requirement(value)
        marker = str(requirement.marker) if requirement.marker else ""
        result.add(
            (
                requirement.name.lower().replace("_", "-"),
                str(requirement.specifier),
                marker,
            )
        )
    return result


def assert_metadata(raw):
    metadata = email.parser.BytesParser().parsebytes(raw)
    assert metadata["Metadata-Version"] == "2.4", metadata["Metadata-Version"]
    assert metadata["Name"] == EXPECTED_NAME, metadata["Name"]
    assert metadata["Version"] == EXPECTED_VERSION, metadata["Version"]
    assert metadata["Summary"] == EXPECTED_SUMMARY, metadata["Summary"]
    assert metadata["Author"] == EXPECTED_AUTHOR, metadata["Author"]
    assert metadata["License-Expression"] == EXPECTED_LICENSE, (
        metadata["License-Expression"], metadata["License"]
    )
    assert set(metadata.get_all("License-File", [])) == {"LICENSE"}, metadata.get_all(
        "License-File", []
    )
    assert not metadata.get_all("Dynamic", []), metadata.get_all("Dynamic", [])
    assert set(metadata.get_all("Classifier", [])) == EXPECTED_CLASSIFIERS, metadata.get_all(
        "Classifier", []
    )
    assert tuple(part.strip() for part in metadata["Keywords"].split(",")) == (
        EXPECTED_KEYWORDS
    ), metadata["Keywords"]
    project_urls = {
        tuple(part.strip() for part in value.split(",", 1))
        for value in metadata.get_all("Project-URL", [])
    }
    assert project_urls == EXPECTED_PROJECT_URLS, project_urls
    assert metadata["Description-Content-Type"].split(";", 1)[0] == "text/markdown", (
        metadata["Description-Content-Type"]
    )
    assert SpecifierSet(metadata["Requires-Python"]) == SpecifierSet(
        EXPECTED_REQUIRES_PYTHON
    ), metadata["Requires-Python"]
    assert canonical_requirements(metadata.get_all("Requires-Dist", [])) == (
        EXPECTED_REQUIRES_DIST
    ), metadata.get_all("Requires-Dist", [])
    return (
        metadata["Name"],
        metadata["Version"],
        str(SpecifierSet(metadata["Requires-Python"])),
        frozenset(canonical_requirements(metadata.get_all("Requires-Dist", []))),
        metadata["Summary"],
        metadata["Author"],
        metadata["License-Expression"],
        frozenset(metadata.get_all("License-File", [])),
        frozenset(metadata.get_all("Classifier", [])),
        tuple(part.strip() for part in metadata["Keywords"].split(",")),
        frozenset(project_urls),
        metadata.get_payload().rstrip("\n"),
    )


def assert_record(archive, names):
    record_names = [name for name in names if name.endswith(".dist-info/RECORD")]
    assert len(record_names) == 1, record_names
    record_name = record_names[0]
    rows = list(
        csv.reader(io.StringIO(archive.read(record_name).decode("utf-8")))
    )
    normalized_rows = [
        (path.replace("\\", "/"), encoded_hash, encoded_size)
        for path, encoded_hash, encoded_size in rows
    ]
    normalized_paths = [path for path, _, _ in normalized_rows]
    assert len(normalized_paths) == len(set(normalized_paths)), rows
    assert set(normalized_paths) == set(names), (record_name, rows)
    for path, encoded_hash, encoded_size in normalized_rows:
        if path == record_name:
            assert encoded_hash == encoded_size == "", (path, encoded_hash, encoded_size)
            continue
        payload = archive.read(path)
        algorithm, expected = encoded_hash.split("=", 1)
        actual = base64.urlsafe_b64encode(
            hashlib.new(algorithm, payload).digest()
        ).rstrip(b"=").decode("ascii")
        assert actual == expected, path
        assert len(payload) == int(encoded_size), path


def main():
    args = parse_args()
    artifact_dir = args.artifact_dir.resolve()
    repository_root = args.repository_root.resolve()
    wheels = sorted(artifact_dir.glob("*.whl"))
    sdists = sorted(artifact_dir.glob("*.tar.gz"))
    universal = [path for path in wheels if path.name.endswith("-py2.py3-none-any.whl")]
    native = [path for path in wheels if path not in universal]

    assert len(universal) == 1, universal
    assert len(native) == args.expected_native_wheels, native
    assert len(sdists) == 1, sdists
    filenames = [path.name for path in [*wheels, *sdists]]
    assert len(filenames) == len(set(filenames)), filenames

    slash = "/"
    backslash = "\\"
    forbidden_text = (
        str(repository_root),
        slash + "workspace" + slash,
        slash + "home" + slash + "runner" + slash + "work" + slash,
        backslash * 2 + "Users" + backslash * 2,
        "target" + slash + "debug",
        "target" + slash + "release",
    )

    canonical_metadata = set()
    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert_safe_paths(names)
            assert not any(
                name.endswith((".pyc", ".pyo"))
                or "/tests/" in "/" + name
                or "/target/" in "/" + name
                for name in names
            ), names
            metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
            assert len(metadata_names) == 1, metadata_names
            canonical_metadata.add(assert_metadata(archive.read(metadata_names[0])))
            assert_record(archive, names)
            license_names = [
                name for name in names if name.endswith(".dist-info/licenses/LICENSE")
            ]
            assert len(license_names) == 1, license_names
            assert archive.read(license_names[0]) == (repository_root / "LICENSE").read_bytes()

            wheel_names = [name for name in names if name.endswith(".dist-info/WHEEL")]
            assert len(wheel_names) == 1, wheel_names
            wheel_text = archive.read(wheel_names[0]).decode("utf-8")

            has_native = any(name.endswith((".so", ".pyd", ".dll")) for name in names)
            if wheel in universal:
                assert not has_native, names
                assert "rfc3339_validator.py" in names, names
                assert "Root-Is-Purelib: true" in wheel_text, wheel_text
                assert "Tag: py2-none-any" in wheel_text, wheel_text
                assert "Tag: py3-none-any" in wheel_text, wheel_text
            else:
                assert has_native, names
                assert "rfc3339_validator/__init__.py" in names, names
                assert any(name.startswith("rfc3339_validator/_native") for name in names), names
                assert "Root-Is-Purelib: false" in wheel_text, wheel_text
                assert "-abi3-" in wheel.name, wheel.name

            for name in names:
                if name.endswith(TEXT_SUFFIXES):
                    text = archive.read(name).decode("utf-8", errors="ignore")
                    assert not any(value in text for value in forbidden_text), name

    with tarfile.open(sdists[0], "r:gz") as archive:
        names = archive.getnames()
        assert_safe_paths(names)
        assert not any(
            "/target/" in "/" + name
            or "/.venv/" in "/" + name
            or "/__pycache__/" in "/" + name
            or "/fallback/build/" in "/" + name
            or ".egg-info/" in "/" + name
            for name in names
        ), names
        required_suffixes = (
            "/Cargo.toml",
            "/pyproject.toml",
            "/src/lib.rs",
            "/python/rfc3339_validator/__init__.py",
            "/fallback/rfc3339_validator.py",
        )
        for suffix in required_suffixes:
            assert any(name.endswith(suffix) for name in names), suffix
        metadata_members = [
            member for member in archive.getmembers() if member.name.endswith("/PKG-INFO")
        ]
        assert len(metadata_members) == 1, [member.name for member in metadata_members]
        metadata_file = archive.extractfile(metadata_members[0])
        assert metadata_file is not None
        canonical_metadata.add(assert_metadata(metadata_file.read()))

    assert len(canonical_metadata) == 1, canonical_metadata

    print(
        "artifact audit: PASS native=%d fallback=1 sdist=1"
        % args.expected_native_wheels
    )


if __name__ == "__main__":
    main()

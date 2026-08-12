#!/usr/bin/env python3
import argparse
import json
import random
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEED = 20260812
CASE_COUNT = 10_000


def generate_cases():
    rng = random.Random(SEED)
    cases = [
        {"kind": "none"},
        {"kind": "int", "value": 1},
        {"kind": "bytes", "value": "2020-01-01T00:00:00Z"},
        {"kind": "str", "value": ""},
        {"kind": "str", "value": "0000-01-01T00:00:00Z"},
        {"kind": "str", "value": "2020-01-01T00:00:00Z\n"},
    ]
    while len(cases) < CASE_COUNT // 2:
        year = rng.randrange(0, 10_000)
        month = rng.randrange(0, 15)
        day = rng.randrange(0, 35)
        hour = rng.randrange(0, 27)
        minute = rng.randrange(0, 65)
        second = rng.randrange(0, 65)
        fraction = "" if rng.randrange(3) == 0 else "." + "".join(
            str(rng.randrange(10)) for _ in range(rng.randrange(0, 12))
        )
        if rng.randrange(2):
            zone = "Z"
        else:
            zone = "%s%02d:%02d" % (
                rng.choice("+-"),
                rng.randrange(0, 27),
                rng.randrange(0, 65),
            )
        value = "%04d-%02d-%02dT%02d:%02d:%02d%s%s" % (
            year,
            month,
            day,
            hour,
            minute,
            second,
            fraction,
            zone,
        )
        if rng.randrange(20) == 0:
            value += "\n"
        cases.append({"kind": "str", "value": value})

    alphabet = "0123456789-T:.+Zzt /_\n\r\x00٠２０"
    while len(cases) < CASE_COUNT:
        value = "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 48)))
        cases.append({"kind": "str", "value": value})
    return cases


def run_probe(python, corpus, output, oracle=None):
    command = [
        str(python.absolute()),
        str(ROOT / "scripts" / "probe_contract.py"),
        "--corpus",
        str(corpus),
        "--output",
        str(output),
    ]
    if oracle:
        command.extend(["--oracle", str(oracle)])
    subprocess.run(command, check=True, cwd=tempfile.gettempdir())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--oracle-python", type=Path, required=True)
    parser.add_argument("--candidate-python", type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="fast-rfc3339-diff-") as directory:
        temporary = Path(directory)
        corpus = temporary / "corpus.jsonl"
        oracle_output = temporary / "oracle.jsonl"
        candidate_output = temporary / "candidate.jsonl"
        cases = generate_cases()
        corpus.write_text(
            "\n".join(json.dumps(case, ensure_ascii=False) for case in cases) + "\n",
            encoding="utf-8",
        )
        run_probe(
            args.oracle_python,
            corpus,
            oracle_output,
            ROOT / "upstream" / "oracle" / "rfc3339_validator.py",
        )
        run_probe(args.candidate_python, corpus, candidate_output)
        oracle_lines = oracle_output.read_text(encoding="utf-8").splitlines()
        candidate_lines = candidate_output.read_text(encoding="utf-8").splitlines()
        if oracle_lines != candidate_lines:
            for index, (oracle, candidate) in enumerate(zip(oracle_lines, candidate_lines)):
                if oracle != candidate:
                    raise AssertionError(
                        "differential mismatch at case %d: oracle=%s candidate=%s"
                        % (index, oracle, candidate)
                    )
            raise AssertionError("differential output cardinality mismatch")
        print("differential: PASS seed=%d cases=%d" % (SEED, len(cases)))


if __name__ == "__main__":
    main()

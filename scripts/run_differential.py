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
    cases = []

    # Constants
    cases.append({"kind": "const", "name": "BITCOIN_ALPHABET"})
    cases.append({"kind": "const", "name": "RIPPLE_ALPHABET"})
    cases.append({"kind": "const", "name": "__version__"})
    cases.append({"kind": "const", "name": "alphabet"})
    for name in (
        "scrub_input",
        "b58encode_int",
        "b58encode",
        "_get_base58_decode_map",
        "b58decode_int",
        "b58decode",
        "b58encode_check",
        "b58decode_check",
    ):
        cases.append({"kind": "metadata", "name": name})

    # Known test vectors
    known = [
        # (func, args, kwargs)
        ("b58encode", [b"hello world"], {}),
        ("b58encode", [b"\x00\x00hello world"], {}),
        ("b58encode", [b""], {}),
        ("b58decode", ["StV1DL6CwTryKyV"], {}),
        ("b58decode", [b"StV1DL6CwTryKyV"], {}),
        ("b58decode", ["11StV1DL6CwTryKyV"], {}),
        ("b58decode", ["1"], {}),
        ("b58decode", [b"1"], {}),
        ("b58encode_check", ["hello world"], {}),
        ("b58decode_check", ["3vQB7B6MrGQZaxCuFg4oh"], {}),
        ("b58decode_check", ["3vQB7B6MrGQZaxCuFg4oH"], {}),
        ("b58encode_int", [0], {}),
        ("b58encode_int", [0], {"default_one": False}),
        ("b58encode_int", [1], {}),
        ("b58decode_int", ["1"], {}),
        ("b58decode_int", ["2"], {}),
        ("scrub_input", ["hello"], {}),
        ("scrub_input", [b"hello"], {}),
        ("scrub_input", ["caf\xe9"], {}),  # non-ASCII should raise
        ("scrub_input", [None], {}),
        ("scrub_input", [1], {}),
        ("scrub_input", [bytearray(b"1")], {}),
        ("scrub_input", [memoryview(b"1")], {}),
        ("b58encode", [None], {}),
        ("b58encode", [bytearray(b"1")], {}),
        ("b58decode_int", [None], {}),
        ("b58decode_int", [bytearray(b"1")], {}),
        ("b58decode", [None], {}),
        ("b58decode", [bytearray(b"1")], {}),
        ("b58decode_int", [b"\x08"], {}),
    ]

    for func, args_list, kwargs in known:
        cases.append({
            "kind": "call",
            "function": func,
            "args": [
                {"kind": "bytes", "value": list(a)} if isinstance(a, bytes)
                else {"kind": "bytearray", "value": list(a)} if isinstance(a, bytearray)
                else {"kind": "memoryview", "value": list(a)} if isinstance(a, memoryview)
                else {"kind": "str", "value": a} if isinstance(a, str)
                else {"kind": "none", "value": None} if a is None
                else {"kind": "int", "value": a}
                for a in args_list
            ],
            "kwargs": {
                k: (
                    {"kind": "bytes", "value": list(v)} if isinstance(v, bytes)
                    else {"kind": "bytearray", "value": list(v)} if isinstance(v, bytearray)
                    else {"kind": "memoryview", "value": list(v)} if isinstance(v, memoryview)
                    else {"kind": "str", "value": v} if isinstance(v, str)
                    else {"kind": "none", "value": None} if v is None
                    else {"kind": "int", "value": v} if isinstance(v, int)
                    else v
                )
                for k, v in kwargs.items()
            },
        })

    # Alphabet cases
    alphabets = [
        list(b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"),
        list(b"rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz"),
        list(b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"),
    ]

    # Generate random encode/decode round-trips
    while len(cases) < CASE_COUNT // 2:
        length = rng.randrange(0, 64)
        data = bytes(rng.randrange(256) for _ in range(length))
        alpha_idx = rng.randrange(len(alphabets))
        alpha = alphabets[alpha_idx]

        # encode
        cases.append({
            "kind": "call",
            "function": "b58encode",
            "args": [{"kind": "bytes", "value": list(data)}],
            "kwargs": {"alphabet": {"kind": "bytes", "value": alpha}},
        })

        # encode_check
        cases.append({
            "kind": "call",
            "function": "b58encode_check",
            "args": [{"kind": "bytes", "value": list(data)}],
            "kwargs": {"alphabet": {"kind": "bytes", "value": alpha}},
        })

    # Random decode attempts (valid and invalid)
    while len(cases) < CASE_COUNT:
        length = rng.randrange(0, 40)
        alpha_idx = rng.randrange(len(alphabets))
        alpha = alphabets[alpha_idx]
        # generate random base58-like strings
        value = bytes(
            rng.choice(alpha)
            for _ in range(length)
        )
        cases.append({
            "kind": "call",
            "function": "b58decode",
            "args": [{"kind": "bytes", "value": list(value)}],
            "kwargs": {"alphabet": {"kind": "bytes", "value": alpha}},
        })

        # b58decode_int
        cases.append({
            "kind": "call",
            "function": "b58decode_int",
            "args": [{"kind": "bytes", "value": list(value)}],
            "kwargs": {"alphabet": {"kind": "bytes", "value": alpha}},
        })

    return cases[:CASE_COUNT]


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

    with tempfile.TemporaryDirectory(prefix="fast-base58-diff-") as directory:
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
            ROOT / "upstream" / "base58" / "__init__.py",
        )
        run_probe(args.candidate_python, corpus, candidate_output)
        oracle_lines = oracle_output.read_text(encoding="utf-8").splitlines()
        candidate_lines = candidate_output.read_text(encoding="utf-8").splitlines()
        if oracle_lines != candidate_lines:
            for index, (oracle_line, candidate_line) in enumerate(
                zip(oracle_lines, candidate_lines)
            ):
                if oracle_line != candidate_line:
                    raise AssertionError(
                        "differential mismatch at case %d:\n  oracle=%s\n  candidate=%s"
                        % (index, oracle_line, candidate_line)
                    )
            raise AssertionError(
                "differential output cardinality mismatch: oracle=%d candidate=%d"
                % (len(oracle_lines), len(candidate_lines))
            )
        print("differential: PASS seed=%d cases=%d" % (SEED, len(cases)))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import hashlib
import importlib.util
import json
import platform
import statistics
import sys
import time
from pathlib import Path


def load_oracle(path):
    spec = importlib.util.spec_from_file_location("frozen_base58_oracle", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen oracle")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def samples_encode(func, values, iterations, repeats, warmup):
    for _ in range(warmup):
        for value in values:
            func(value)
    output = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        for index in range(iterations):
            func(values[index % len(values)])
        elapsed = time.perf_counter_ns() - start
        output.append(elapsed / iterations)
    return output


def samples_decode(func, values, iterations, repeats, warmup, **kwargs):
    for _ in range(warmup):
        for value in values:
            func(value, **kwargs)
    output = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        for index in range(iterations):
            func(values[index % len(values)], **kwargs)
        elapsed = time.perf_counter_ns() - start
        output.append(elapsed / iterations)
    return output


def summarize(raw):
    ordered = sorted(raw)
    p95_index = max(0, min(len(ordered) - 1, int(len(ordered) * 0.95) - 1))
    return {
        "raw_ns_per_call": raw,
        "median_ns_per_call": statistics.median(raw),
        "p95_ns_per_call": ordered[p95_index],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=100_000)
    parser.add_argument("--repeats", type=int, default=15)
    parser.add_argument("--warmup", type=int, default=10_000)
    args = parser.parse_args()

    import base58 as candidate

    artifact = args.artifact.resolve()
    artifact_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()

    root = Path(__file__).resolve().parents[1]
    oracle = load_oracle(root / "upstream" / "base58" / "__init__.py")

    # Prepare workloads
    small_data = b"hello world"
    medium_data = bytes(range(256)) * 4  # 1024 bytes
    large_data = bytes(range(256)) * 16  # 4096 bytes

    small_encoded = candidate.b58encode(small_data)
    medium_encoded = candidate.b58encode(medium_data)
    large_encoded = candidate.b58encode(large_data)

    workloads = {
        "encode_small": ("encode", [small_data], {}),
        "encode_medium": ("encode", [medium_data], {}),
        "encode_large": ("encode", [large_data], {}),
        "decode_small": ("decode", [small_encoded], {}),
        "decode_medium": ("decode", [medium_encoded], {}),
        "decode_large": ("decode", [large_encoded], {}),
    }

    result = {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "candidate_file": candidate.__file__,
        "artifact": artifact.name,
        "artifact_sha256": artifact_sha256,
        "iterations": args.iterations,
        "repeats": args.repeats,
        "warmup": args.warmup,
        "workloads": {},
    }

    for name, (op, values, kwargs) in workloads.items():
        if op == "encode":
            oracle_raw = samples_encode(
                oracle.b58encode, values,
                args.iterations, args.repeats, args.warmup
            )
            candidate_raw = samples_encode(
                candidate.b58encode, values,
                args.iterations, args.repeats, args.warmup
            )
        else:
            oracle_raw = samples_decode(
                oracle.b58decode, values,
                args.iterations, args.repeats, args.warmup
            )
            candidate_raw = samples_decode(
                candidate.b58decode, values,
                args.iterations, args.repeats, args.warmup
            )

        oracle_summary = summarize(oracle_raw)
        candidate_summary = summarize(candidate_raw)
        speedup = (
            oracle_summary["median_ns_per_call"]
            / candidate_summary["median_ns_per_call"]
            if candidate_summary["median_ns_per_call"] > 0
            else float("inf")
        )
        result["workloads"][name] = {
            "input_sizes": [len(v) for v in values],
            "oracle": oracle_summary,
            "candidate": candidate_summary,
            "median_speedup": speedup,
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

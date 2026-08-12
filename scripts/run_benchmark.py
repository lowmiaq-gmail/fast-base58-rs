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
    spec = importlib.util.spec_from_file_location("frozen_rfc3339_oracle", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen oracle")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def samples(function, values, iterations, repeats, warmup):
    for _ in range(warmup):
        for value in values:
            function(value)
    output = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        for index in range(iterations):
            function(values[index % len(values)])
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

    import rfc3339_validator as candidate

    artifact = args.artifact.resolve()
    artifact_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()

    root = Path(__file__).resolve().parents[1]
    oracle = load_oracle(root / "upstream" / "oracle" / "rfc3339_validator.py")
    workloads = {
        "valid_z": ["2020-02-29T23:59:59.123456Z"],
        "valid_offset": ["2024-01-31T08:09:10+23:59"],
        "mixed": [
            "2020-02-29T23:59:59Z",
            "2019-02-29T00:00:00Z",
            "2020-01-01t00:00:00z",
            "2020-01-01T00:00:00.123+08:00",
        ],
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
    for name, values in workloads.items():
        oracle_raw = samples(
            oracle.validate_rfc3339, values, args.iterations, args.repeats, args.warmup
        )
        candidate_raw = samples(
            candidate.validate_rfc3339, values, args.iterations, args.repeats, args.warmup
        )
        oracle_summary = summarize(oracle_raw)
        candidate_summary = summarize(candidate_raw)
        result["workloads"][name] = {
            "input": values,
            "oracle": oracle_summary,
            "candidate": candidate_summary,
            "median_speedup": oracle_summary["median_ns_per_call"]
            / candidate_summary["median_ns_per_call"],
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

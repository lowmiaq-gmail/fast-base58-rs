# Benchmark

Semantic equality was established before measurement through the candidate suite, the complete frozen upstream suite, and an isolated 10,000-case differential run.

## Local packaged-wheel result

- artifact: `fast_rfc3339_validator_rs-0.1.0-cp38-abi3-macosx_11_0_arm64.whl`
- artifact SHA256: `e198eb30b858e1efc86b5773ae29d0ed7e05df0de4f7a70a5a8f7481d93c050c`
- hardware: Apple M4 Pro, arm64
- OS: macOS 26.5.2
- Python: CPython 3.14.6
- warmup: 10,000 calls per workload
- measurement: 15 repeats × 100,000 calls
- unit: nanoseconds per call

| Workload | Oracle median | Candidate median | Oracle p95 | Candidate p95 | Median speedup |
|---|---:|---:|---:|---:|---:|
| valid UTC with fraction | 896.76 | 132.71 | 996.26 | 169.68 | 6.76x |
| valid maximum offset | 820.10 | 120.01 | 933.25 | 143.31 | 6.83x |
| mixed valid/invalid | 738.94 | 127.16 | 858.66 | 130.85 | 5.81x |

The committed JSON contains every raw sample, exact inputs, interpreter string and artifact import path. Reproduce with:

```bash
python scripts/run_benchmark.py \
  --artifact /path/to/fast_rfc3339_validator_rs-0.1.0-cp38-abi3-macosx_11_0_arm64.whl \
  --output benchmarks/local-macos-arm64-python314.json \
  --iterations 100000 --repeats 15 --warmup 10000
```

These numbers describe this machine and artifact only; they are not a universal speed guarantee.

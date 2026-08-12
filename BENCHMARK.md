# Benchmark

Semantic equality was established before measurement through the candidate suite, the complete frozen upstream suite, and an isolated 10,000-case differential run.

## Local packaged-wheel result

Benchmarks are recorded truthfully after all equality gates pass. Results are specific to the machine, artifact, and workload.

The committed JSON contains every raw sample, exact inputs, interpreter string and artifact import path. Reproduce with:

```bash
python scripts/run_benchmark.py \
  --artifact /path/to/fast_base58_rs-0.1.0-cp38-abi3-macosx_11_0_arm64.whl \
  --output benchmarks/local-macos-arm64-python314.json \
  --iterations 100000 --repeats 15 --warmup 10000
```

These numbers describe this machine and artifact only; they are not a universal speed guarantee.

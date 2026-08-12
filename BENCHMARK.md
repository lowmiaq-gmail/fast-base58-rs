# Benchmark

Semantic equality was established before measurement through the candidate suite, the complete frozen upstream suite, and an isolated 10,000-case differential run.

## Local packaged-wheel result

Benchmarks are recorded truthfully after all equality gates pass. Results are specific to the machine, artifact, and workload.

The fixed workloads are representative 16-byte identifiers, 32-byte keys, and
64-byte signatures. The committed JSON contains every raw sample, exact input
sizes, interpreter string and artifact import path. Reproduce with:

| Operation | Payload | Oracle median ns | Candidate median ns | Median ratio |
|---|---:|---:|---:|---:|
| encode | 16 bytes | 8,205.12 | 2,008.83 | 4.08x |
| encode | 32 bytes | 17,536.50 | 4,743.22 | 3.70x |
| encode | 64 bytes | 42,331.32 | 15,535.93 | 2.72x |
| decode | 16 bytes | 6,186.61 | 8,883.17 | 0.70x |
| decode | 32 bytes | 9,459.19 | 8,755.13 | 1.08x |
| decode | 64 bytes | 20,009.68 | 16,510.14 | 1.21x |

The encode fast path was faster for all three measured sizes. Decode was faster
for 32-byte and 64-byte payloads but slower for the 16-byte payload, so this
release does not make an across-the-board decode speed claim.

```bash
python scripts/run_benchmark.py \
  --artifact /path/to/fast_base58_rs-0.1.0-cp38-abi3-macosx_11_0_arm64.whl \
  --output benchmarks/local-macos-arm64-python314.json \
  --iterations 10000 --repeats 15 --warmup 1000
```

These numbers describe this machine and artifact only; they are not a universal speed guarantee.
Large multi-kilobyte inputs are outside the measured fast-path claim.

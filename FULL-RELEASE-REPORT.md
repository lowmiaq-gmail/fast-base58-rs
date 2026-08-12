# Full Release Report

Target release: `0.1.0`.

## Passed locally

- Rust fmt, clippy with `-D warnings`, and all-target tests: PASS.
- candidate contract tests: PASS (`87` independent-verifier tests on the packaged native wheel).
- complete unfiltered upstream suite: PASS (`48` collected test cases across `test_base58.py` and `test_base45.py`).
- isolated Oracle/Candidate differential: PASS (`seed=20260812`, `10,000` cases) for native and universal fallback.
- independent targeted/fuzz verification: PASS (`9,000` additional calls, zero mismatch), including duplicate/malformed alphabets, dynamic truthiness, integer subclasses, exact exceptions, cache state, and CLI byte-for-byte behavior.
- exact-commit local candidate set: one macOS arm64 abi3 wheel, one `py3-none-any` fallback wheel, one sdist.
- `packaging`-backed canonical metadata/WHEEL/RECORD/license/path audit and `twine check`: PASS; both wheels have zero Dynamic fields and the sdist contains no generated debris.
- fresh packaged native-wheel selection/import/semantics: PASS.
- fresh packaged fallback-wheel candidate/upstream/differential gates: PASS.
- fresh wheel rebuilt from the sdist passed candidate and complete upstream suites.
- local packaged-wheel benchmark: PASS with `15` raw samples per workload, median/p95, environment, exact artifact SHA256, and truthful positive/negative ratios recorded in `benchmarks/local-macos-arm64-python314.json`.

## Required before completion count

- cross-platform CI and packaged native wheels;
- Python 3.7 fallback artifact execution;
- public GitHub repository metadata and immutable release workflow;
- PyPI Trusted Publishing and public-index reinstall lanes;
- formal GitHub Release created last with checksums;
- post-release monitoring and SEO report.

Status: `IN PROGRESS — NOT RELEASED, NOT COUNTED`.

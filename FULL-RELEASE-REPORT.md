# Full Release Report

Target release: `0.1.0`.

## Passed locally

- Rust fmt, clippy with `-D warnings`, and all-target tests: PASS.
- candidate contract tests: PASS.
- complete unfiltered upstream suite: PASS (30 tests across test_base58.py and test_base45.py).
- isolated Oracle/Candidate differential: PASS (`seed=20260812`, `10,000` cases) for native and universal fallback.
- exact-commit local candidate set: one macOS arm64 abi3 wheel, one `py3-none-any` fallback wheel, one sdist.
- `packaging`-backed canonical metadata/WHEEL/RECORD/license/path audit and `twine check`: PASS; both wheels have zero Dynamic fields and the sdist contains no generated debris.
- fresh packaged native-wheel selection/import/semantics: PASS.
- fresh packaged fallback-wheel candidate/upstream/differential gates: PASS.
- fresh wheel rebuilt from the sdist passed candidate and complete upstream suites.
- benchmark raw samples and exact artifact SHA256: regenerated from the exact-commit native candidate after equality gates.

## Required before completion count

- cross-platform CI and packaged native wheels;
- Python 3.7 fallback artifact execution;
- independent verification on the validated commit;
- public GitHub repository metadata and immutable release workflow;
- PyPI Trusted Publishing and public-index reinstall lanes;
- formal GitHub Release created last with checksums;
- post-release monitoring and SEO report.

Status: `IN PROGRESS — NOT RELEASED, NOT COUNTED`.

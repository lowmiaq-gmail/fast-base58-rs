# fast-rfc3339-validator-rs

Rust-backed drop-in replacement for [`rfc3339-validator==0.1.4`](https://pypi.org/project/rfc3339-validator/0.1.4/).

```bash
pip uninstall -y rfc3339-validator
pip install fast-rfc3339-validator-rs
```

Existing imports stay unchanged:

```python
from rfc3339_validator import validate_rfc3339

assert validate_rfc3339("2020-02-29T23:59:59Z")
assert not validate_rfc3339("2019-02-29T00:00:00Z")
```

## Compatibility

The project freezes upstream version `0.1.4` and preserves its function signature, bool return type, regex/calendar semantics, public constants and modules, version metadata, invalid-type exceptions, silent `python -m rfc3339_validator` behavior, and complete upstream test suite.

Modern supported platforms install an abi3 PyO3 wheel. Python 2.7, Python 3.5–3.7, and platforms without a matching native wheel can install the same-version universal fallback wheel. The fallback is the frozen upstream implementation, not a reduced API.

See [COMPATIBILITY.md](COMPATIBILITY.md), [UPSTREAM-CONTRACT.md](UPSTREAM-CONTRACT.md), and [REUSE-AUDIT.md](REUSE-AUDIT.md).

## Performance

After semantic equality passed, the exact-commit macOS arm64 abi3 wheel demonstrated multi-fold speedups across the recorded workloads on Apple M4 Pro / Python 3.14.6. Results are workload- and machine-specific; the measured range, raw samples, exact wheel SHA256, and reproduction details are in [BENCHMARK.md](BENCHMARK.md) and [`benchmarks/local-macos-arm64-python314.json`](benchmarks/local-macos-arm64-python314.json).

## Verification

```bash
cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-targets
python scripts/run_differential.py \
  --oracle-python /path/to/oracle-venv/bin/python \
  --candidate-python /path/to/candidate-venv/bin/python
PYTHON=/path/to/candidate-venv/bin/python bash scripts/run_upstream_full.sh
```

Release counting remains fail-closed until cross-platform packaged wheels, immutable artifacts, PyPI public reinstalls, formal GitHub Release last, and post-release monitoring all pass. See [FULL-RELEASE-REPORT.md](FULL-RELEASE-REPORT.md).

## Migration and rollback

Migration changes only the installed distribution name; the Python import remains `rfc3339_validator`. To roll back:

```bash
pip uninstall -y fast-rfc3339-validator-rs
pip install rfc3339-validator==0.1.4
```

## License

MIT. The frozen upstream implementation is also MIT; attribution is retained in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

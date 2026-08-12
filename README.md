# fast-base58-rs

Rust-backed drop-in replacement for [`base58==2.1.1`](https://pypi.org/project/base58/2.1.1/).

```bash
pip uninstall -y base58
pip install fast-base58-rs
```

Existing imports stay unchanged:

```python
import base58

assert base58.b58encode(b"hello world") == b"StV1DL6CwTryKyV"
assert base58.b58decode("StV1DL6CwTryKyV") == b"hello world"
```

## Compatibility

The project freezes upstream version `2.1.1` and preserves its complete public surface: all encoding/decoding functions, `BITCOIN_ALPHABET`, `RIPPLE_ALPHABET`, `XRP_ALPHABET`, `alphabet` alias, integer API, arbitrary byte alphabet support, `autofix` keyword-only parameter, checksum functions, `__version__`, `py.typed`, console script `base58`, `python -m base58` CLI, `_get_base58_decode_map` with `lru_cache`, and the complete upstream test suite.

Modern supported platforms install an abi3 PyO3 wheel. Python 3.7 and platforms without a matching native wheel can install the same-version pure-Python fallback wheel. The fallback is the frozen upstream implementation, not a reduced API.

See [COMPATIBILITY.md](COMPATIBILITY.md), [UPSTREAM-CONTRACT.md](UPSTREAM-CONTRACT.md), and [REUSE-AUDIT.md](REUSE-AUDIT.md).

## Performance

After semantic equality passed, benchmarks are recorded truthfully. Results are workload- and machine-specific; the measured range, raw samples, exact wheel SHA256, and reproduction details are in [BENCHMARK.md](BENCHMARK.md).

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

Release `v0.1.0` passed the cross-platform packaged-wheel matrix, immutable artifact audit, public PyPI reinstall gates, and formal GitHub Release-last gate. See [FULL-RELEASE-REPORT.md](FULL-RELEASE-REPORT.md) and the [formal release](https://github.com/lowmiaq-gmail/fast-base58-rs/releases/tag/v0.1.0).

## Migration and rollback

Migration changes only the installed distribution name; the Python import remains `base58`. To roll back:

```bash
pip uninstall -y fast-base58-rs
pip install base58==2.1.1
```

## License

MIT. The frozen upstream implementation is also MIT; attribution is retained in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

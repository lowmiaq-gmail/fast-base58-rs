# Executable compatibility matrix

## Runtime and artifact routing

| Runtime | Required artifact | Required proof |
|---|---|---|
| CPython 3.8+ on Linux x86-64/ARM64, macOS x86-64/ARM64, Windows x86-64 | `cp38-abi3` native wheel | extension suffix/loader proves native ownership; candidate contract, full upstream suite, and differential pass |
| Python 3.7 | `py3-none-any` fallback wheel | ordinary install selects fallback; candidate contract and full frozen suite pass |
| Modern unsupported native platform / PyPy | `py3-none-any` fallback wheel | ordinary install and the same contract gates; no Rust-speed claim |

Both wheel families use distribution `fast-base58-rs==0.1.0`, canonical
`Requires-Python: >=3.7`, no runtime dependencies (stdlib only),
and import `base58`. The `cp38-abi3` wheel tag—not divergent core metadata—limits
the native artifact. When both wheel families are compatible, pip must select the platform native wheel;
the installed module suffix/loader is asserted. The release also contains one native-capable sdist.
All artifacts are collected, audited, and published as one immutable set.

## Contract matrix

| Area | Native | Fallback | Executable assertion |
|---|---|---|---|
| Alphabet constants | required | required | `BITCOIN_ALPHABET`, `RIPPLE_ALPHABET`, `XRP_ALPHABET`, `alphabet` identity and value |
| encode/decode round-trip | required | required | frozen upstream 30-test suite across 3 alphabets |
| Integer API | required | required | `b58encode_int`, `b58decode_int` with keyword-only autofix |
| Checksum API | required | required | `b58encode_check`, `b58decode_check` with exact error message |
| Arbitrary alphabet | required | required | BASE45 45-char alphabet, any bytes alphabet |
| `scrub_input` | required | required | str→bytes, bytes pass-through, UnicodeEncodeError |
| `_get_base58_decode_map` | required | required | lru_cache surface, autofix groups, Mapping[int,int] return |
| `__version__` | required | required | `'2.1.1'` |
| CLI / module entry | required | required | `base58` console script, `python -m base58` |
| Invalid characters | required | required | ValueError with exact `{!r}` format message |
| Whitespace rules | required | required | rstrip when space not in alphabet |
| Performance | measured only after parity | no speed claim | isolated benchmark, never a compatibility substitute |

## Required local commands

```bash
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-targets
.venv/bin/maturin develop
.venv/bin/python -m pytest -q tests
.venv/bin/python -m pytest -q upstream/test_base58.py upstream/test_base45.py
.venv/bin/python scripts/run_differential.py \
  --oracle-python .venv/bin/python \
  --candidate-python .venv/bin/python
```

Artifact and release gates must additionally:

1. build native wheels for five release platforms, the universal fallback wheel, and sdist;
2. install packaged wheels rather than editable/source imports;
3. test fallback under Python 3.7;
4. assert native wheel selection on modern supported platforms and fallback selection on legacy runtimes;
5. audit filenames, METADATA, namespace ownership, record hashes, and absence of unexpected files;
6. publish that exact immutable set with Trusted Publishing;
7. reinstall from public PyPI for all lanes and rerun applicable complete gates;
8. create the formal GitHub Release last, then pass launch monitoring.

Any uncovered Python version, artifact-selection ambiguity, public reinstall failure, or
contract mismatch sets the release state to `BLOCKED`; it cannot be converted into a reduced
compatibility claim and counted complete.

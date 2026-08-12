# Executable compatibility matrix

## Runtime and artifact routing

| Runtime | Required artifact | Required proof |
|---|---|---|
| CPython 3.8+ on Linux x86-64/ARM64, macOS x86-64/ARM64, Windows x86-64 | `cp38-abi3` native wheel | extension suffix/loader proves native ownership; candidate contract, full upstream suite, and differential pass |
| Python 2.7 | `py2.py3-none-any` fallback wheel | ordinary install selects fallback; frozen suite passes with only its own Python-2 marker skip |
| Python 3.5, 3.6, 3.7 | `py2.py3-none-any` fallback wheel | ordinary install selects fallback; candidate contract and full frozen suite pass |
| Python 3.0–3.4 | unsupported by upstream | package metadata must exclude these versions |
| Modern unsupported native platform / PyPy | `py2.py3-none-any` fallback wheel | ordinary install and the same contract gates; no Rust-speed claim |

Both wheel families use distribution `fast-rfc3339-validator-rs==0.1.0`, canonical
`Requires-Python: >=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*`, dependency `six`,
and import `rfc3339_validator`. The `cp38-abi3` wheel tag—not divergent core metadata—limits
the native artifact. When both wheel families are compatible, pip must select the platform native wheel;
the installed module suffix/loader is asserted. Legacy runtimes must select the universal
fallback. The release also contains one native-capable sdist. All artifacts are collected,
audited, and published as one immutable set.

## Contract matrix

| Area | Native | Fallback | Executable assertion |
|---|---|---|---|
| Signature/result | required | required | `(date_string)`, exact `bool` |
| Calendar/RFC3339 behavior | required | required | frozen upstream 3-test suite |
| Regex global | required | required | Oracle `.pattern`, `.flags`, type, value |
| `RFC3339_REGEX_FLAGS` | `re.ASCII`, not `re.VERBOSE | re.ASCII` | Oracle per runtime | compare type and value with Oracle |
| Observable modules | required | required | `calendar`, `re`, `six` identity |
| Invalid types | required | required | exception type and exact message differential |
| One final newline | required | required | Oracle/Candidate differential |
| Metadata | required | required | author/email/upstream/replacement versions |
| CLI / module entry | absent | absent | no console entry point; module execution emits no output |
| Performance | measured only after parity | no speed claim | isolated benchmark, never a compatibility substitute |

## Required local commands

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
.venv/bin/maturin develop
.venv/bin/python -m pytest -q tests
.venv/bin/python -m pytest -q upstream/tests
.venv/bin/python scripts/run_differential.py \
  --oracle-python .venv/bin/python \
  --candidate-python .venv/bin/python
```

Artifact and release gates must additionally:

1. build native wheels for five release platforms, the universal fallback wheel, and sdist;
2. install packaged wheels rather than editable/source imports;
3. test fallback under Python 2.7, 3.5, 3.6, and 3.7;
4. assert native wheel selection on modern supported platforms and fallback selection on legacy runtimes;
5. audit filenames, METADATA, namespace ownership, record hashes, and absence of unexpected files;
6. publish that exact immutable set with Trusted Publishing;
7. reinstall from public PyPI for all lanes and rerun applicable complete gates;
8. create the formal GitHub Release last, then pass launch monitoring.

Any uncovered Python version, artifact-selection ambiguity, public reinstall failure, or
contract mismatch sets the release state to `BLOCKED`; it cannot be converted into a reduced
compatibility claim and counted complete.

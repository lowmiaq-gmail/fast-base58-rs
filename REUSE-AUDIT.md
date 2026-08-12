# Reuse audit

## Decision

`rfc3339-validator==0.1.4` is `BUILD`.

- User repositories and the local workspace contained no unfinished Rust/PyO3/Maturin replacement before selection.
- GitHub repository search for `rfc3339-validator rust pyo3` returned no replacement.
- PyPI returned HTTP 404 for `fast-rfc3339-validator-rs`, `rfc3339-validator-rs`, and `rfc3339-validator-rust` at selection time.
- Generic Rust RFC3339 parsers are reusable implementation references, not drop-in replacements: the frozen Python package has regex-specific edge behavior, observable module globals, legacy Python support, and exact exception boundaries.

The target is not a partial accelerator. It must replace the complete `rfc3339_validator`
module contract and its full Python support range. If the native/fallback artifact strategy
cannot prove that range, release is blocked.

## Reused assets

- Upstream tag `v0.1.4`, commit `5ebeb83a83ae5a65e610ffd90de36d30d7161aec`.
- The exact MIT-licensed upstream module and test file under `upstream/`.
- The upstream universal-wheel strategy for legacy Python, retained as a fallback lane.
- The pipeline production protocol and release-gate structure proven by `fast-dotenv-rs`.

No performance or compatibility claim is inherited from a generic Rust crate.

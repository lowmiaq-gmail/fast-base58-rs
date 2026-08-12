# Reuse audit

## Decision

`base58==2.1.1` is `ADAPT`. The existing Rust crate `based58` by kevinheavey uses the
generic `bs58` Rust crate for Base58/Bitcoin alphabet encoding/decoding but explicitly
lacks str inputs, the exact `base58` namespace, integer API (`b58encode_int`/`b58decode_int`),
`autofix` parameter, `RIPPLE_ALPHABET`/`XRP_ALPHABET`, arbitrary byte alphabet support,
`alphabet` retro alias, `scrub_input`, `_get_base58_decode_map`, `b58encode_check`/
`b58decode_check`, `__main__` CLI, `base58` console script entry point, `__version__`,
`py.typed`, and the frozen upstream test suite.

The target is not a partial accelerator. It must replace the complete `base58`
module contract and its full Python support range. If the native/fallback artifact strategy
cannot prove that range, release is blocked.

## Reused assets

- Upstream tag `v2.1.1`, commit `11c293f4479fafffbc7b766fcb703a835c02dccd`.
- PyPI wheel SHA256 `11a36f4d3ce51dfc1043f3218591ac4eb1ceb172919cebe05b52a5bcc8d245c2`; sdist SHA256 `c5d0cb3f5b6e81e8e35da5754388ddcc6d0d14b6c6a132cb93d69ed580a7278c`.
- The exact MIT-licensed upstream module, test files, and CLI entry point under `upstream/`.
- The upstream pure-Python strategy for legacy Python, retained as a fallback lane.
- The pipeline production protocol and release-gate structure proven by `fast-dotenv-rs` and `fast-rfc3339-validator-rs`.

No performance or compatibility claim is inherited from a generic Rust crate.
The `bs58` Rust crate is not used; arbitrary-byte-alphabet support and the full upstream
contract require a bespoke implementation.

# fast-base58-rs 0.1.0

Initial Rust-backed replacement for `base58==2.1.1`.

- Existing `import base58` code remains unchanged.
- Native abi3 wheels cover supported modern platforms.
- A pure-Python fallback preserves the frozen API on Python 3.7 and unsupported native platforms.
- The release artifacts are created once, audited, published through PyPI Trusted Publishing, reinstalled from public PyPI, checksummed, and attached to a formal GitHub Release last.

Measured performance claims are limited to the reproducible results in `BENCHMARK.md`.

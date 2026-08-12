# fast-rfc3339-validator-rs 0.1.0

Initial Rust-backed replacement for `rfc3339-validator==0.1.4`.

- Existing `import rfc3339_validator` code remains unchanged.
- Native abi3 wheels cover supported modern platforms.
- A universal fallback preserves the frozen API on Python 2.7, Python 3.5–3.7 and unsupported native platforms.
- The release artifacts are created once, audited, published through PyPI Trusted Publishing, reinstalled from public PyPI, checksummed, and attached to a formal GitHub Release last.

Measured performance claims are limited to the reproducible results in `BENCHMARK.md`.

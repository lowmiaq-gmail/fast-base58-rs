# Third-Party Notices

## bs58

The native 58-character fast path uses the `bs58` Rust crate, licensed under
MIT OR Apache-2.0. Its source and license metadata are resolved by the locked
Cargo dependency graph.

This project derives its compatibility contract and fallback implementation from `base58` by David Keijser, version 2.1.1, under the MIT License. The original `COPYING`, author metadata, frozen source and unmodified tests are retained.

This project has no runtime dependencies beyond the Python standard library. Test-only dependency `PyHamcrest` is used as required by the frozen upstream suite and is not bundled into release wheels.

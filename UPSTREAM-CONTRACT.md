# Frozen upstream contract

## Identity

| Field | Frozen value |
|---|---|
| Distribution | `base58` |
| Import module | `base58` |
| Version | `2.1.1` |
| Repository | <https://github.com/keis/base58> |
| Tag / commit | `v2.1.1` / `11c293f4479fafffbc7b766fcb703a835c02dccd` |
| License | MIT; upstream `COPYING` SHA256 `2cc1a54227464813f4e149123c2323071009957586f89aca1cc80a9a04d34933` |
| Runtime dependency | none (stdlib only) |
| Python | `>=3.7` |
| sdist | `base58-2.1.1.tar.gz`, SHA256 `c5d0cb3f5b6e81e8e35da5754388ddcc6d0d14b6c6a132cb93d69ed580a7278c` |
| wheel | `base58-2.1.1-py3-none-any.whl`, SHA256 `11a36f4d3ce51dfc1043f3218591ac4eb1ceb172919cebe05b52a5bcc8d245c2` |

Frozen local files:

- `upstream/base58/__init__.py`: upstream implementation
- `upstream/base58/__main__.py`: upstream CLI entry point
- `upstream/base58/py.typed`: upstream marker
- `upstream/test_base58.py`: upstream test suite
- `upstream/test_base45.py`: upstream arbitrary-alphabet test suite

## Public and observable surface

### Module-level constants
- `__version__`: `'2.1.1'`
- `BITCOIN_ALPHABET`: `b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'` (58 chars)
- `RIPPLE_ALPHABET`: `b'rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz'` (58 chars)
- `XRP_ALPHABET`: identity alias for `RIPPLE_ALPHABET` (same object, not just same value)
- `alphabet`: retro-compatibility alias for `BITCOIN_ALPHABET` (same object)

### Public functions (signatures exactly as upstream)

- `scrub_input(v: Union[str, bytes]) -> bytes`: if str, encode to ascii bytes; return unchanged if bytes
- `b58encode_int(i: int, default_one: bool = True, alphabet: bytes = BITCOIN_ALPHABET) -> bytes`: encode integer as base58
- `b58encode(v: Union[str, bytes], alphabet: bytes = BITCOIN_ALPHABET) -> bytes`: encode string/bytes as base58
- `_get_base58_decode_map(alphabet: bytes, autofix: bool) -> Mapping[int, int]`: build decode map (decorated with `@lru_cache()`)
- `b58decode_int(v: Union[str, bytes], alphabet: bytes = BITCOIN_ALPHABET, *, autofix: bool = False) -> int`: decode base58 to integer; `autofix` is keyword-only
- `b58decode(v: Union[str, bytes], alphabet: bytes = BITCOIN_ALPHABET, *, autofix: bool = False) -> bytes`: decode base58 to bytes
- `b58encode_check(v: Union[str, bytes], alphabet: bytes = BITCOIN_ALPHABET) -> bytes`: encode with 4-byte checksum (double SHA256)
- `b58decode_check(v: Union[str, bytes], alphabet: bytes = BITCOIN_ALPHABET, *, autofix: bool = False) -> bytes`: decode and verify checksum; raises `ValueError("Invalid checksum")` on mismatch

### Module entry point and CLI

- `python -m base58`: runs the CLI (`base58/__main__.py`)
- Console script `base58`: entry point to `base58.__main__:main`
- CLI supports file/stdin input with `-d`/`--decode` and `-c`/`--check` flags
- `py.typed`: present, enables PEP 561 typing

### Module docstring
- The module has the upstream docstring: `'''Base58 encoding\n\nImplementations of Base58 and Base58Check encodings that are compatible\nwith the bitcoin network.\n'''`

## Behavioral boundaries

- `scrub_input`: str → `v.encode('ascii')`; bytes → pass through. Raises `UnicodeEncodeError` for non-ASCII str.
- `b58encode_int(0, default_one=True)` → `alphabet[0:1]` (single first-char byte). `b58encode_int(0, default_one=False)` → `b''`.
- `b58encode(b'')` → `b''`. Leading null bytes become leading alphabet[0] characters.
- `b58encode(b'\x00\x00hello world')` → `b'11StV1DL6CwTryKyV'`.
- `b58decode('')` → `b''` (empty input after rstrip); `b58decode('1')` → `b'\x00'`.
- `b58decode` whitespace handling: if `b' '` is NOT in alphabet, `v.rstrip()` strips trailing whitespace before decode. If `b' '` IS in alphabet (e.g. BASE45), no stripping occurs.
- `b58decode_int` whitespace: same rstrip rule; then decode (no leading-char stripping — that's only in b58decode).
- `b58decode_int` raises `ValueError("Invalid character {!r}".format(chr(byte)))` for bytes not in decode map. The `{!r}` produces `repr(chr(byte))` — e.g. `"Invalid character '\\\\x08'"` for backspace, `"Invalid character '0'"` for `'0'` not in bitcoin alphabet.
- `autofix=True`: groups `[b'0Oo']` and `[b'Il1']` — if exactly one character in a group appears in the alphabet, all group members map to its index.
- `_get_base58_decode_map` is decorated with `@lru_cache()` (maxsize=128, typed=False).
- `b58decode_check` raises `ValueError("Invalid checksum")` on checksum mismatch.
- `b58decode_int` autofix is keyword-only (after `*` in signature). Calling it as positional raises `TypeError`.
- `b58decode` autofix is keyword-only. Same for `b58decode_check`.
- Imported module attributes `functools`, `hashlib`, `typing` are observable via `from base58 import *`.
- `XRP_ALPHABET is RIPPLE_ALPHABET` evaluates to `True`.

## Complete upstream suite

The frozen suites are exactly the unmodified:

- `upstream/test_base58.py`: 18 tests including parametrized alphabet round-trips, integer encoding, autofix, checksum, invalid input, random benchmark tests.
- `upstream/test_base45.py`: 12 tests using the 45-character alphabet `b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"`.

No test selection, custom xfail, deletion, or mutation is allowed.

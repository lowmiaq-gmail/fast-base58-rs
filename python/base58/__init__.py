'''Base58 encoding

Implementations of Base58 and Base58Check encodings that are compatible
with the bitcoin network.
'''

from functools import lru_cache
from hashlib import sha256
from typing import Mapping, Union

from base58._native import (
    BITCOIN_ALPHABET,
    RIPPLE_ALPHABET,
    XRP_ALPHABET,
    __version__,
    alphabet,
    b58decode as _native_b58decode,
    b58decode_int as _native_b58decode_int,
    b58encode as _native_b58encode,
    b58encode_check as _native_b58encode_check,
    b58encode_int as _native_b58encode_int,
)


def scrub_input(v: Union[str, bytes]) -> bytes:
    if isinstance(v, str):
        v = v.encode('ascii')

    return v


def b58encode_int(
    i: int, default_one: bool = True, alphabet: bytes = BITCOIN_ALPHABET
) -> bytes:
    """
    Encode an integer using Base58
    """
    if (
        type(i) is int
        and i >= 0
        and type(default_one) is bool
        and type(alphabet) is bytes
        and 2 <= len(alphabet) <= 256
    ):
        return _native_b58encode_int(i, default_one, alphabet)

    if not i and default_one:
        return alphabet[0:1]
    string = b""
    base = len(alphabet)
    while i:
        i, idx = divmod(i, base)
        string = alphabet[idx:idx+1] + string
    return string


def b58encode(
    v: Union[str, bytes], alphabet: bytes = BITCOIN_ALPHABET
) -> bytes:
    """
    Encode a string using Base58
    """
    v = scrub_input(v)

    origlen = len(v)
    stripped = v.lstrip(b'\0')
    newlen = len(stripped)

    if type(v) is bytes and type(alphabet) is bytes and 2 <= len(alphabet) <= 256:
        return _native_b58encode(v, alphabet)

    acc = int.from_bytes(stripped, byteorder='big')
    result = b58encode_int(acc, default_one=False, alphabet=alphabet)
    return alphabet[0:1] * (origlen - newlen) + result


@lru_cache()
def _get_base58_decode_map(alphabet: bytes,
                           autofix: bool) -> Mapping[int, int]:
    invmap = {char: index for index, char in enumerate(alphabet)}

    if autofix:
        groups = [b'0Oo', b'Il1']
        for group in groups:
            pivots = [c for c in group if c in invmap]
            if len(pivots) == 1:
                for alternative in group:
                    invmap[alternative] = invmap[pivots[0]]

    return invmap


def b58decode_int(
    v: Union[str, bytes], alphabet: bytes = BITCOIN_ALPHABET, *,
    autofix: bool = False
) -> int:
    """
    Decode a Base58 encoded string as an integer
    """
    if b' ' not in alphabet:
        v = v.rstrip()
    v = scrub_input(v)

    map = _get_base58_decode_map(alphabet, autofix=autofix)

    if (
        type(v) is bytes
        and type(alphabet) is bytes
        and 2 <= len(alphabet) <= 256
        and len(set(alphabet)) == len(alphabet)
        and type(autofix) is bool
    ):
        return _native_b58decode_int(v, alphabet, autofix=autofix)

    decimal = 0
    base = len(alphabet)
    try:
        for char in v:
            decimal = decimal * base + map[char]
    except KeyError as e:
        raise ValueError(
            "Invalid character {!r}".format(chr(e.args[0]))
        ) from None
    return decimal


def b58decode(
    v: Union[str, bytes], alphabet: bytes = BITCOIN_ALPHABET, *,
    autofix: bool = False
) -> bytes:
    """
    Decode a Base58 encoded string
    """
    v = v.rstrip()
    v = scrub_input(v)

    origlen = len(v)
    stripped = v.lstrip(alphabet[0:1])
    newlen = len(stripped)

    native_compatible = (
        type(v) is bytes
        and type(alphabet) is bytes
        and 2 <= len(alphabet) <= 256
        and len(set(alphabet)) == len(alphabet)
        and type(autofix) is bool
    )
    if native_compatible:
        _get_base58_decode_map(alphabet, autofix=autofix)
        return _native_b58decode(v, alphabet, autofix=autofix)

    acc = b58decode_int(stripped, alphabet=alphabet, autofix=autofix)
    return acc.to_bytes(origlen - newlen + (acc.bit_length() + 7) // 8, 'big')


def b58encode_check(
    v: Union[str, bytes], alphabet: bytes = BITCOIN_ALPHABET
) -> bytes:
    """
    Encode a string using Base58 with a 4 character checksum
    """
    v = scrub_input(v)

    if type(v) is bytes and type(alphabet) is bytes and 2 <= len(alphabet) <= 256:
        return _native_b58encode_check(v, alphabet)

    digest = sha256(sha256(v).digest()).digest()
    return b58encode(v + digest[:4], alphabet=alphabet)


def b58decode_check(
    v: Union[str, bytes], alphabet: bytes = BITCOIN_ALPHABET, *,
    autofix: bool = False
) -> bytes:
    '''Decode and verify the checksum of a Base58 encoded string'''

    result = b58decode(v, alphabet=alphabet, autofix=autofix)
    result, check = result[:-4], result[-4:]
    digest = sha256(sha256(result).digest()).digest()

    if check != digest[:4]:
        raise ValueError("Invalid checksum")

    return result

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
    _get_base58_decode_map as _native_get_base58_decode_map,
    alphabet,
    b58decode,
    b58decode_check,
    b58decode_int,
    b58encode,
    b58encode_check,
    b58encode_int,
    scrub_input,
)


@lru_cache()
def _get_base58_decode_map(alphabet, autofix):
    return _native_get_base58_decode_map(alphabet, autofix)

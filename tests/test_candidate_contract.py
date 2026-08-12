import importlib.util
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

import base58 as candidate


def load_oracle():
    path = Path(__file__).parents[1] / "upstream" / "base58" / "__init__.py"
    spec = importlib.util.spec_from_file_location("frozen_base58_oracle", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── module constants ─────────────────────────────────────────────

def test_version():
    assert candidate.__version__ == "2.1.1"


def test_alphabet_constants():
    assert candidate.BITCOIN_ALPHABET == (
        b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    )
    assert candidate.RIPPLE_ALPHABET == (
        b"rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz"
    )
    assert candidate.XRP_ALPHABET is candidate.RIPPLE_ALPHABET
    assert candidate.alphabet is candidate.BITCOIN_ALPHABET


def test_module_docstring():
    oracle = load_oracle()
    assert candidate.__doc__ == oracle.__doc__
    assert "Base58 encoding" in candidate.__doc__


def test_star_import():
    oracle = load_oracle()
    namespace = {}
    exec("from base58 import *", namespace)
    actual = {name for name in namespace if not name.startswith("_")}
    expected = {name for name in vars(oracle) if not name.startswith("_")}
    assert actual == expected


# ── function signatures ──────────────────────────────────────────

def test_scrub_input_signature():
    sig = str(inspect.signature(candidate.scrub_input))
    assert "v" in sig


def test_b58encode_int_signature():
    sig = str(inspect.signature(candidate.b58encode_int))
    assert "i" in sig
    assert "default_one" in sig
    assert "alphabet" in sig


def test_b58encode_signature():
    sig = str(inspect.signature(candidate.b58encode))
    assert "v" in sig
    assert "alphabet" in sig


def test_b58decode_int_signature_keyword_only():
    sig = str(inspect.signature(candidate.b58decode_int))
    assert "*, autofix" in sig


def test_b58decode_signature_keyword_only():
    sig = str(inspect.signature(candidate.b58decode))
    assert "*, autofix" in sig


def test_b58decode_check_signature_keyword_only():
    sig = str(inspect.signature(candidate.b58decode_check))
    assert "*, autofix" in sig


# ── encode / decode round-trips ──────────────────────────────────

@pytest.mark.parametrize("alphabet_name", ["BITCOIN_ALPHABET", "RIPPLE_ALPHABET"])
def test_roundtrip_hello_world(alphabet_name):
    alphabet = getattr(candidate, alphabet_name)
    assert candidate.b58decode(
        candidate.b58encode(b"hello world", alphabet=alphabet),
        alphabet=alphabet,
    ) == b"hello world"


def test_encode_hello_world():
    assert candidate.b58encode(b"hello world") == b"StV1DL6CwTryKyV"


def test_encode_leading_zeros():
    assert candidate.b58encode(b"\x00\x00hello world") == b"11StV1DL6CwTryKyV"


def test_encode_empty():
    assert candidate.b58encode(b"") == b""


def test_decode_hello_world_str():
    assert candidate.b58decode("StV1DL6CwTryKyV") == b"hello world"


def test_decode_hello_world_bytes():
    assert candidate.b58decode(b"StV1DL6CwTryKyV") == b"hello world"


def test_decode_leading_zeros():
    assert candidate.b58decode("11StV1DL6CwTryKyV") == b"\x00\x00hello world"


def test_decode_single_one():
    assert candidate.b58decode("1") == b"\x00"


def test_decode_single_one_bytes():
    assert candidate.b58decode(b"1") == b"\x00"


# ── integer API ──────────────────────────────────────────────────

def test_b58encode_int_basic():
    assert candidate.b58encode_int(0) == b"1"
    assert candidate.b58encode_int(0, default_one=False) == b""
    assert candidate.b58encode_int(1) == b"2"


def test_b58decode_int_basic():
    assert candidate.b58decode_int(b"1") == 0
    assert candidate.b58decode_int(b"2") == 1


# ── checksum ─────────────────────────────────────────────────────

def test_check_roundtrip():
    out = candidate.b58encode_check("hello world")
    assert out == b"3vQB7B6MrGQZaxCuFg4oh"
    back = candidate.b58decode_check(out)
    assert back == b"hello world"


def test_check_failure():
    with pytest.raises(ValueError, match="Invalid checksum"):
        candidate.b58decode_check("3vQB7B6MrGQZaxCuFg4oH")


# ── autofix ──────────────────────────────────────────────────────

def test_autofix_decode():
    data = candidate.b58decode(b"StVlDL6CwTryKyV", autofix=True)
    assert data == b"hello world"


def test_autofix_check():
    data = candidate.b58decode_check("3vQB7B6MrGQZaxCuFg4Oh", autofix=True)
    assert data == b"hello world"


# ── arbitrary alphabet (BASE45) ──────────────────────────────────

BASE45_ALPHABET = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"


def test_base45_encode():
    data = candidate.b58encode(b"hello world", alphabet=BASE45_ALPHABET)
    assert data == b"K3*J+EGLBVAYYB36"


def test_base45_decode():
    data = candidate.b58decode("K3*J+EGLBVAYYB36", alphabet=BASE45_ALPHABET)
    assert data == b"hello world"


def test_base45_decode_single_one():
    # alphabet[0] is '0', so '1' is index 1 → b'\x01'
    assert candidate.b58decode("1", alphabet=BASE45_ALPHABET) == b"\x01"


# ── whitespace rules ─────────────────────────────────────────────

def test_whitespace_stripping_no_space_in_alphabet():
    # bitcoin alphabet has no space, so rstrip is applied
    assert candidate.b58decode("StV1DL6CwTryKyV  ") == b"hello world"
    assert candidate.b58decode("StV1DL6CwTryKyV\n") == b"hello world"


def test_whitespace_no_stripping_with_space_in_alphabet():
    # b58decode always rstrips whitespace regardless of alphabet
    encoded = candidate.b58encode(b"test", alphabet=BASE45_ALPHABET)
    # trailing space is stripped even though space is in BASE45 alphabet
    decoded_with_space = candidate.b58decode(encoded + b" ", alphabet=BASE45_ALPHABET)
    decoded_without = candidate.b58decode(encoded, alphabet=BASE45_ALPHABET)
    assert decoded_with_space == decoded_without == b"test"


# ── error boundaries ─────────────────────────────────────────────

def test_invalid_character_error():
    with pytest.raises(ValueError, match="Invalid character"):
        candidate.b58decode("xyz\x08")


def test_scrub_input_non_ascii_str():
    with pytest.raises(UnicodeEncodeError):
        candidate.scrub_input("café")


def test_b58decode_int_autofix_keyword_only():
    # autofix must be keyword-only
    with pytest.raises(TypeError):
        candidate.b58decode_int("1", candidate.BITCOIN_ALPHABET, True)


# ── CLI ──────────────────────────────────────────────────────────

def test_console_script_registered():
    import importlib.metadata
    eps = importlib.metadata.entry_points()
    # The console_scripts group should contain base58
    console_scripts = []
    if hasattr(eps, 'select'):
        console_scripts = [ep for ep in eps.select(group='console_scripts')]
    else:
        console_scripts = [ep for ep in eps.get('console_scripts', [])]
    script_names = [ep.name for ep in console_scripts]
    assert "base58" in script_names


def test_cli_encode_stdin():
    result = subprocess.run(
        [sys.executable, "-m", "base58"],
        input=b"hello world",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == b"StV1DL6CwTryKyV"


def test_cli_decode_stdin():
    result = subprocess.run(
        [sys.executable, "-m", "base58", "-d"],
        input=b"StV1DL6CwTryKyV\n",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == b"hello world"


def test_cli_check_roundtrip():
    result = subprocess.run(
        [sys.executable, "-m", "base58", "-c"],
        input=b"hello world",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    encoded = result.stdout.strip()
    result2 = subprocess.run(
        [sys.executable, "-m", "base58", "-d", "-c"],
        input=encoded + b"\n",
        capture_output=True,
        check=False,
    )
    assert result2.returncode == 0
    assert result2.stdout == b"hello world"


# ── lru_cache surface ────────────────────────────────────────────

def test_get_base58_decode_map_is_cached():
    map1 = candidate._get_base58_decode_map(candidate.BITCOIN_ALPHABET, False)
    map2 = candidate._get_base58_decode_map(candidate.BITCOIN_ALPHABET, False)
    # lru_cache returns same object for same args
    assert map1 is map2


# ── large integer ────────────────────────────────────────────────

def test_large_integer():
    number = 0x111D38E5FC9071FFCD20B4A763CC9AE4F252BB4E48FD66A835E252ADA93FF480D6DD43DC62A641155A5  # noqa
    assert candidate.b58decode_int(candidate.BITCOIN_ALPHABET) == number
    assert candidate.b58encode_int(number) == candidate.BITCOIN_ALPHABET[1:]

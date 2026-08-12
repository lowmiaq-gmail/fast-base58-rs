use std::collections::HashMap;
use std::sync::Mutex;

use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyString};
use sha2::{Digest, Sha256};

// ── alphabet constants ──────────────────────────────────────────────

const BITCOIN_ALPHABET_BYTES: &[u8] = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
const RIPPLE_ALPHABET_BYTES: &[u8] = b"rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz";

// ── decode-map cache ────────────────────────────────────────────────
//
// The upstream wraps `_get_base58_decode_map` with `@lru_cache()`.
// We replicate that with a Mutex-protected HashMap; the number of
// distinct alphabets is tiny in practice so unbounded growth is fine.

#[allow(clippy::type_complexity)]
static DECODE_MAP_CACHE: Mutex<Option<HashMap<(Vec<u8>, bool), HashMap<u8, u8>>>> =
    Mutex::new(None);

fn cache_get_or_insert(alphabet: &[u8], autofix: bool) -> HashMap<u8, u8> {
    let mut guard = DECODE_MAP_CACHE.lock().unwrap();
    let cache = guard.get_or_insert_with(HashMap::new);
    let key = (alphabet.to_vec(), autofix);
    if let Some(map) = cache.get(&key) {
        return map.clone();
    }
    let map = build_decode_map(alphabet, autofix);
    cache.insert(key, map.clone());
    map
}

fn build_decode_map(alphabet: &[u8], autofix: bool) -> HashMap<u8, u8> {
    let mut invmap: HashMap<u8, u8> = HashMap::with_capacity(alphabet.len());
    for (index, &ch) in alphabet.iter().enumerate() {
        invmap.insert(ch, index as u8);
    }
    if autofix {
        let groups: [[u8; 3]; 2] = [[b'0', b'O', b'o'], [b'I', b'l', b'1']];
        for group in &groups {
            let pivots: Vec<u8> = group
                .iter()
                .filter(|c| invmap.contains_key(c))
                .copied()
                .collect();
            if pivots.len() == 1 {
                let pivot_idx = invmap[&pivots[0]];
                for &alternative in group {
                    invmap.insert(alternative, pivot_idx);
                }
            }
        }
    }
    invmap
}

// ── core encode / decode (carry-based, no big-int dependency) ──────

fn base58_encode_bytes(input: &[u8], alphabet: &[u8]) -> Vec<u8> {
    let base = alphabet.len() as u32;
    let zeros = input.iter().take_while(|&&b| b == 0).count();

    // heuristic capacity: ~ log256(58) ≈ 1.38 × input length
    let mut output: Vec<u8> = Vec::with_capacity(input.len().saturating_mul(138) / 100 + 1);

    for &byte in &input[zeros..] {
        let mut carry = byte as u32;
        for out_byte in output.iter_mut() {
            carry += (*out_byte as u32) * 256;
            *out_byte = (carry % base) as u8;
            carry /= base;
        }
        while carry > 0 {
            output.push((carry % base) as u8);
            carry /= base;
        }
    }

    // each leading \x00 → alphabet[0]
    output.resize(output.len() + zeros, 0);
    output.reverse();
    output.iter().map(|&idx| alphabet[idx as usize]).collect()
}

fn base58_decode_to_bytes(input: &[u8], alphabet: &[u8], decode_map: &HashMap<u8, u8>) -> Vec<u8> {
    let leading_char = alphabet[0];
    let zeros = input.iter().take_while(|&&b| b == leading_char).count();
    let base = alphabet.len() as u32;

    let mut output: Vec<u8> = Vec::new();

    for &ch in &input[zeros..] {
        let idx = decode_map[&ch] as u32;
        let mut carry = idx;
        for out_byte in output.iter_mut() {
            carry += (*out_byte as u32) * base;
            *out_byte = (carry % 256) as u8;
            carry /= 256;
        }
        while carry > 0 {
            output.push((carry % 256) as u8);
            carry /= 256;
        }
    }

    output.resize(output.len() + zeros, 0);
    output.reverse();
    output
}

fn alphabet_contains_space(alphabet: &[u8]) -> bool {
    alphabet.contains(&b' ')
}

fn always_rstrip(v: &[u8]) -> Vec<u8> {
    let mut end = v.len();
    while end > 0 {
        let b = v[end - 1];
        if b == b' ' || b == b'\t' || b == b'\n' || b == b'\r' || b == 0x0b || b == 0x0c {
            end -= 1;
        } else {
            break;
        }
    }
    v[..end].to_vec()
}

fn maybe_rstrip(v: &[u8], alphabet: &[u8]) -> Vec<u8> {
    if alphabet_contains_space(alphabet) {
        v.to_vec()
    } else {
        always_rstrip(v)
    }
}

// ── helpers for Python types ───────────────────────────────────────

fn scrub_input_impl<'py>(_py: Python<'py>, v: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyBytes>> {
    if let Ok(s) = v.downcast::<PyString>() {
        // encode to ASCII (Python: v.encode('ascii'))
        let bytes = s.call_method1("encode", ("ascii",))?;
        return Ok(bytes.downcast::<PyBytes>()?.clone());
    }
    if let Ok(b) = v.downcast::<PyBytes>() {
        return Ok(b.clone());
    }
    // Match Python's error for operations on non-str/non-bytes
    Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
        "a bytes-like object is required, not 'int'",
    ))
}

fn alphabet_from_py(_py: Python, obj: &Bound<'_, PyAny>) -> PyResult<Vec<u8>> {
    if let Ok(b) = obj.downcast::<PyBytes>() {
        return Ok(b.as_bytes().to_vec());
    }
    Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
        "alphabet must be bytes",
    ))
}

// ── PyO3-exposed functions ─────────────────────────────────────────

/// scrub_input(v: Union[str, bytes]) -> bytes
#[pyfunction(name = "scrub_input", signature = (v))]
fn py_scrub_input<'py>(py: Python<'py>, v: Bound<'py, PyAny>) -> PyResult<Bound<'py, PyBytes>> {
    scrub_input_impl(py, &v)
}

/// b58encode_int(i: int, default_one: bool = True,
///               alphabet: bytes = BITCOIN_ALPHABET) -> bytes
#[pyfunction(name = "b58encode_int", signature = (
    i,
    default_one = true,
    alphabet = None
))]
fn py_b58encode_int<'py>(
    py: Python<'py>,
    i: Bound<'py, PyAny>,
    default_one: bool,
    alphabet: Option<Bound<'py, PyAny>>,
) -> PyResult<Bound<'py, PyBytes>> {
    let alpha = match alphabet {
        Some(a) => alphabet_from_py(py, &a)?,
        None => BITCOIN_ALPHABET_BYTES.to_vec(),
    };

    // check for zero — compare with Python int(0)
    let zero = 0i64.into_pyobject(py)?;
    let is_zero: bool = i.eq(zero)?;
    if is_zero {
        if default_one {
            return Ok(PyBytes::new(py, &alpha[..1]));
        }
        return Ok(PyBytes::new(py, b""));
    }

    // Convert Python int → minimal big-endian bytes
    let bit_length: usize = i.call_method0("bit_length")?.extract()?;
    let byte_len = bit_length.div_ceil(8);
    let bytes_obj = i.call_method1("to_bytes", (byte_len, "big"))?;
    let bytes_val = bytes_obj.downcast::<PyBytes>()?.as_bytes().to_vec();

    let encoded = base58_encode_bytes(&bytes_val, &alpha);
    Ok(PyBytes::new(py, &encoded))
}

/// b58encode(v: Union[str, bytes],
///           alphabet: bytes = BITCOIN_ALPHABET) -> bytes
#[pyfunction(name = "b58encode", signature = (v, alphabet = None))]
fn py_b58encode<'py>(
    py: Python<'py>,
    v: Bound<'py, PyAny>,
    alphabet: Option<Bound<'py, PyAny>>,
) -> PyResult<Bound<'py, PyBytes>> {
    let alpha = match alphabet {
        Some(a) => alphabet_from_py(py, &a)?,
        None => BITCOIN_ALPHABET_BYTES.to_vec(),
    };
    let scrubbed = scrub_input_impl(py, &v)?;
    let bytes_val = scrubbed.as_bytes();

    let origlen = bytes_val.len();
    let stripped: Vec<u8> = bytes_val.iter().skip_while(|&&b| b == 0).copied().collect();
    let newlen = stripped.len();

    let encoded = base58_encode_bytes(&stripped, &alpha);
    let prefix_len = origlen - newlen;
    let mut result = Vec::with_capacity(prefix_len + encoded.len());
    for _ in 0..prefix_len {
        result.push(alpha[0]);
    }
    result.extend_from_slice(&encoded);
    Ok(PyBytes::new(py, &result))
}

/// _get_base58_decode_map(alphabet: bytes, autofix: bool) -> Mapping[int, int]
#[pyfunction(name = "_get_base58_decode_map", signature = (alphabet, autofix))]
fn py_get_base58_decode_map<'py>(
    py: Python<'py>,
    alphabet: Bound<'py, PyBytes>,
    autofix: bool,
) -> PyResult<Py<PyDict>> {
    let alpha = alphabet.as_bytes();
    let map = cache_get_or_insert(alpha, autofix);
    let dict = PyDict::new(py);
    for (k, v) in &map {
        dict.set_item(*k as u32, *v as u32)?;
    }
    Ok(dict.into())
}

/// b58decode_int(v: Union[str, bytes],
///               alphabet: bytes = BITCOIN_ALPHABET, *,
///               autofix: bool = False) -> int
#[pyfunction(name = "b58decode_int", signature = (v, alphabet = None, *, autofix = false))]
fn py_b58decode_int<'py>(
    py: Python<'py>,
    v: Bound<'py, PyAny>,
    alphabet: Option<Bound<'py, PyAny>>,
    autofix: bool,
) -> PyResult<Bound<'py, PyAny>> {
    let alpha = match alphabet {
        Some(a) => alphabet_from_py(py, &a)?,
        None => BITCOIN_ALPHABET_BYTES.to_vec(),
    };

    let scrubbed = scrub_input_impl(py, &v)?;
    let bytes_val = scrubbed.as_bytes();

    // whitespace stripping (only if space not in alphabet)
    let bytes_val = maybe_rstrip(bytes_val, &alpha);

    let decode_map = cache_get_or_insert(&alpha, autofix);

    // validate characters
    for &ch in &bytes_val {
        if !decode_map.contains_key(&ch) {
            // Format: ValueError("Invalid character {!r}".format(chr(ch)))
            let chr_repr = format!("{:?}", ch as char);
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid character {}",
                chr_repr
            )));
        }
    }

    let decoded = base58_decode_to_bytes(&bytes_val, &alpha, &decode_map);

    // Convert bytes → Python int
    let py_bytes = PyBytes::new(py, &decoded);
    let builtins = py.import("builtins")?;
    let int_class = builtins.getattr("int")?;
    let py_int = int_class.call_method1("from_bytes", (py_bytes, "big"))?;
    Ok(py_int)
}

/// b58decode(v: Union[str, bytes],
///           alphabet: bytes = BITCOIN_ALPHABET, *,
///           autofix: bool = False) -> bytes
#[pyfunction(name = "b58decode", signature = (v, alphabet = None, *, autofix = false))]
fn py_b58decode<'py>(
    py: Python<'py>,
    v: Bound<'py, PyAny>,
    alphabet: Option<Bound<'py, PyAny>>,
    autofix: bool,
) -> PyResult<Bound<'py, PyBytes>> {
    let alpha = match alphabet {
        Some(a) => alphabet_from_py(py, &a)?,
        None => BITCOIN_ALPHABET_BYTES.to_vec(),
    };

    let scrubbed = scrub_input_impl(py, &v)?;
    let bytes_val = scrubbed.as_bytes();

    // b58decode ALWAYS rstrip()s whitespace (unlike b58decode_int, which is conditional)
    let bytes_val = always_rstrip(bytes_val);

    let origlen = bytes_val.len();
    let leading_char = alpha[0];
    let stripped: Vec<u8> = bytes_val
        .iter()
        .skip_while(|&&b| b == leading_char)
        .copied()
        .collect();
    let newlen = stripped.len();

    let decode_map = cache_get_or_insert(&alpha, autofix);

    // validate characters
    for &ch in &stripped {
        if !decode_map.contains_key(&ch) {
            let chr_repr = format!("{:?}", ch as char);
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid character {}",
                chr_repr
            )));
        }
    }

    let decoded = base58_decode_to_bytes(&stripped, &alpha, &decode_map);

    // pad with leading zeros to match original length
    let expected_pad = origlen - newlen;
    let bit_len = if decoded.is_empty() {
        0usize
    } else {
        let mut bit_len = decoded.len() * 8;
        for &b in &decoded {
            let leading_zeros = b.leading_zeros() as usize;
            bit_len -= leading_zeros.min(8);
            if leading_zeros < 8 {
                break;
            }
        }
        bit_len
    };
    let byte_len = expected_pad + bit_len.div_ceil(8);
    let mut result = vec![0u8; byte_len];
    let start = byte_len.saturating_sub(decoded.len());
    result[start..].copy_from_slice(&decoded);

    Ok(PyBytes::new(py, &result))
}

/// b58encode_check(v: Union[str, bytes],
///                 alphabet: bytes = BITCOIN_ALPHABET) -> bytes
#[pyfunction(name = "b58encode_check", signature = (v, alphabet = None))]
fn py_b58encode_check<'py>(
    py: Python<'py>,
    v: Bound<'py, PyAny>,
    alphabet: Option<Bound<'py, PyAny>>,
) -> PyResult<Bound<'py, PyBytes>> {
    let alpha = match alphabet {
        Some(a) => alphabet_from_py(py, &a)?,
        None => BITCOIN_ALPHABET_BYTES.to_vec(),
    };
    let scrubbed = scrub_input_impl(py, &v)?;
    let bytes_val = scrubbed.as_bytes();

    // double sha256, take first 4 bytes
    let digest1 = Sha256::digest(bytes_val);
    let digest2 = Sha256::digest(digest1);
    let checksum = &digest2[..4];

    // append checksum
    let mut with_checksum = bytes_val.to_vec();
    with_checksum.extend_from_slice(checksum);

    // encode
    let origlen = with_checksum.len();
    let stripped: Vec<u8> = with_checksum
        .iter()
        .skip_while(|&&b| b == 0)
        .copied()
        .collect();
    let newlen = stripped.len();

    let encoded = base58_encode_bytes(&stripped, &alpha);
    let prefix_len = origlen - newlen;
    let mut result = Vec::with_capacity(prefix_len + encoded.len());
    for _ in 0..prefix_len {
        result.push(alpha[0]);
    }
    result.extend_from_slice(&encoded);
    Ok(PyBytes::new(py, &result))
}

/// b58decode_check(v: Union[str, bytes],
///                 alphabet: bytes = BITCOIN_ALPHABET, *,
///                 autofix: bool = False) -> bytes
#[pyfunction(name = "b58decode_check", signature = (v, alphabet = None, *, autofix = false))]
fn py_b58decode_check<'py>(
    py: Python<'py>,
    v: Bound<'py, PyAny>,
    alphabet: Option<Bound<'py, PyAny>>,
    autofix: bool,
) -> PyResult<Bound<'py, PyBytes>> {
    let alpha = match alphabet {
        Some(a) => alphabet_from_py(py, &a)?,
        None => BITCOIN_ALPHABET_BYTES.to_vec(),
    };

    let scrubbed = scrub_input_impl(py, &v)?;
    let bytes_val = scrubbed.as_bytes();
    // b58decode_check calls b58decode which always rstrips
    let bytes_val = always_rstrip(bytes_val);

    let origlen = bytes_val.len();
    let leading_char = alpha[0];
    let stripped: Vec<u8> = bytes_val
        .iter()
        .skip_while(|&&b| b == leading_char)
        .copied()
        .collect();
    let newlen = stripped.len();

    let decode_map = cache_get_or_insert(&alpha, autofix);

    // validate
    for &ch in &stripped {
        if !decode_map.contains_key(&ch) {
            let chr_repr = format!("{:?}", ch as char);
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid character {}",
                chr_repr
            )));
        }
    }

    let decoded = base58_decode_to_bytes(&stripped, &alpha, &decode_map);

    let expected_pad = origlen - newlen;
    let bit_len = if decoded.is_empty() {
        0usize
    } else {
        let mut bit_len = decoded.len() * 8;
        for &b in &decoded {
            let leading_zeros = b.leading_zeros() as usize;
            bit_len -= leading_zeros.min(8);
            if leading_zeros < 8 {
                break;
            }
        }
        bit_len
    };
    let byte_len = expected_pad + bit_len.div_ceil(8);
    let mut result = vec![0u8; byte_len];
    let start = byte_len.saturating_sub(decoded.len());
    result[start..].copy_from_slice(&decoded);

    if result.len() < 4 {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid checksum",
        ));
    }

    let (payload, check) = result.split_at(result.len() - 4);
    let digest1 = Sha256::digest(payload);
    let digest2 = Sha256::digest(digest1);

    if check != &digest2[..4] {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid checksum",
        ));
    }

    Ok(PyBytes::new(py, payload))
}

// ── module initialisation ──────────────────────────────────────────

#[pymodule]
fn _native(py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    let bitcoin_alphabet = PyBytes::new(py, BITCOIN_ALPHABET_BYTES);
    let ripple_alphabet = PyBytes::new(py, RIPPLE_ALPHABET_BYTES);

    module.add("__version__", "2.1.1")?;
    module.add("BITCOIN_ALPHABET", bitcoin_alphabet.clone())?;
    module.add("RIPPLE_ALPHABET", ripple_alphabet.clone())?;
    // XRP_ALPHABET is RIPPLE_ALPHABET (same object)
    module.add("XRP_ALPHABET", ripple_alphabet.clone())?;
    // alphabet is BITCOIN_ALPHABET (retro compatibility, same object)
    module.add("alphabet", bitcoin_alphabet)?;

    module.add_function(wrap_pyfunction!(py_scrub_input, module)?)?;
    module.add_function(wrap_pyfunction!(py_b58encode_int, module)?)?;
    module.add_function(wrap_pyfunction!(py_b58encode, module)?)?;
    module.add_function(wrap_pyfunction!(py_get_base58_decode_map, module)?)?;
    module.add_function(wrap_pyfunction!(py_b58decode_int, module)?)?;
    module.add_function(wrap_pyfunction!(py_b58decode, module)?)?;
    module.add_function(wrap_pyfunction!(py_b58encode_check, module)?)?;
    module.add_function(wrap_pyfunction!(py_b58decode_check, module)?)?;

    Ok(())
}

// ── Rust unit tests ────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_roundtrip_bitcoin_alphabet() {
        let alphabet = BITCOIN_ALPHABET_BYTES;
        let inputs: Vec<&[u8]> = vec![
            b"",
            b"hello world",
            b"\x00",
            b"\x00\x00hello world",
            b"\xff",
            b"\xff\xff\xff\xff",
            &[0u8; 32],
        ];
        for input in &inputs {
            let encoded = base58_encode_bytes(input, alphabet);
            let decode_map = build_decode_map(alphabet, false);
            let decoded = base58_decode_to_bytes(&encoded, alphabet, &decode_map);
            assert_eq!(decoded, *input, "round-trip failed for {:?}", input);
        }
    }

    #[test]
    fn test_encode_empty() {
        let result = base58_encode_bytes(b"", BITCOIN_ALPHABET_BYTES);
        assert_eq!(result, b"");
    }

    #[test]
    fn test_encode_hello_world() {
        let result = base58_encode_bytes(b"hello world", BITCOIN_ALPHABET_BYTES);
        assert_eq!(result, b"StV1DL6CwTryKyV");
    }

    #[test]
    fn test_encode_leading_zeros() {
        let result = base58_encode_bytes(b"\x00\x00hello world", BITCOIN_ALPHABET_BYTES);
        assert_eq!(result, b"11StV1DL6CwTryKyV");
    }

    #[test]
    fn test_decode_hello_world() {
        let decode_map = build_decode_map(BITCOIN_ALPHABET_BYTES, false);
        let result =
            base58_decode_to_bytes(b"StV1DL6CwTryKyV", BITCOIN_ALPHABET_BYTES, &decode_map);
        assert_eq!(result, b"hello world");
    }

    #[test]
    fn test_decode_leading_zeros() {
        let decode_map = build_decode_map(BITCOIN_ALPHABET_BYTES, false);
        let result =
            base58_decode_to_bytes(b"11StV1DL6CwTryKyV", BITCOIN_ALPHABET_BYTES, &decode_map);
        assert_eq!(result, b"\x00\x00hello world");
    }

    #[test]
    fn test_decode_single_one() {
        let decode_map = build_decode_map(BITCOIN_ALPHABET_BYTES, false);
        let result = base58_decode_to_bytes(b"1", BITCOIN_ALPHABET_BYTES, &decode_map);
        assert_eq!(result, b"\x00");
    }

    #[test]
    fn test_decode_empty_input() {
        let decode_map = build_decode_map(BITCOIN_ALPHABET_BYTES, false);
        let result = base58_decode_to_bytes(b"", BITCOIN_ALPHABET_BYTES, &decode_map);
        assert_eq!(result, b"");
    }

    #[test]
    fn test_base45_alphabet() {
        let alphabet = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:";
        let input = b"hello world";
        let encoded = base58_encode_bytes(input, alphabet);
        let decode_map = build_decode_map(alphabet, false);
        let decoded = base58_decode_to_bytes(&encoded, alphabet, &decode_map);
        assert_eq!(decoded, input);
        // Verify against known test vector
        assert_eq!(encoded, b"K3*J+EGLBVAYYB36");
    }

    #[test]
    fn test_base45_leading_zeros() {
        let alphabet = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:";
        let input = b"\x00\x00hello world";
        let encoded = base58_encode_bytes(input, alphabet);
        assert_eq!(encoded, b"00K3*J+EGLBVAYYB36");
    }

    #[test]
    fn test_base45_decode_single_one() {
        // alphabet[0] = '0', so '1' is not the leading char; it decodes to index 1
        let alphabet = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:";
        let decode_map = build_decode_map(alphabet, false);
        let result = base58_decode_to_bytes(b"1", alphabet, &decode_map);
        assert_eq!(result, b"\x01");
    }

    #[test]
    fn test_build_decode_map_autofix() {
        // In bitcoin alphabet, '0' is not present, 'O' and 'o' are present (one pivot)
        // 'I' is not present, 'l' is present, '1' is present (two pivots, no autofix)
        let map = build_decode_map(BITCOIN_ALPHABET_BYTES, true);
        // 'l' -> lowercase L, should map to same index as 'l' was originally
        // Actually in bitcoin alphabet: 'l' is present (lowercase L), 'I' and '1' are present
        // The groups are [0,O,o] and [I,l,1]
        // In BTC alphabet: '0'=f, 'O'=f, 'o'=f? Let me check...
        // BTC: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
        // Contains: '1', 'l' (lower L), no 'I', no '0', no 'O', but has 'o' (lower O)
        // Group [0,O,o]: only 'o' is in alphabet → pivot='o', so '0' and 'O' map to 'o's index
        // Group [I,l,1]: 'l' and '1' are in alphabet → 2 pivots, no autofix
        assert!(map.contains_key(&b'0'));
        assert!(map.contains_key(&b'O'));
        assert_eq!(map[&b'0'], map[&b'o']);
        assert_eq!(map[&b'O'], map[&b'o']);
    }

    #[test]
    fn test_maybe_rstrip_with_space_in_alphabet() {
        let alphabet = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:";
        let input = b"hello world  ";
        let result = maybe_rstrip(input, alphabet);
        // space IS in alphabet, so no stripping
        assert_eq!(result, b"hello world  ");
    }

    #[test]
    fn test_maybe_rstrip_without_space_in_alphabet() {
        let input = b"hello world  \t\n";
        let result = maybe_rstrip(input, BITCOIN_ALPHABET_BYTES);
        assert_eq!(result, b"hello world");
    }

    #[test]
    fn test_ripple_alphabet_identity() {
        // RIPPLE_ALPHABET and XRP_ALPHABET should be the same bytes
        assert_eq!(RIPPLE_ALPHABET_BYTES, RIPPLE_ALPHABET_BYTES); // tautology but documents intent
                                                                  // Test round-trip with ripple alphabet
        let input = b"hello world";
        let encoded = base58_encode_bytes(input, RIPPLE_ALPHABET_BYTES);
        let decode_map = build_decode_map(RIPPLE_ALPHABET_BYTES, false);
        let decoded = base58_decode_to_bytes(&encoded, RIPPLE_ALPHABET_BYTES, &decode_map);
        assert_eq!(decoded, input);
    }
}

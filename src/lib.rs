use pyo3::prelude::*;
use pyo3::types::{PyAny, PyModule, PyString};

const RFC3339_PATTERN: &str = r#"
    ^
    (\d{4})      # Year
    -
    (0[1-9]|1[0-2]) # Month
    -
    (\d{2})          # Day
    T
    (?:[01]\d|2[0123]) # Hours
    :
    (?:[0-5]\d)     # Minutes
    :
    (?:[0-5]\d)     # Seconds
    (?:\.\d+)?      # Secfrac
    (?:  Z                              # UTC
       | [+-](?:[01]\d|2[0123]):[0-5]\d # Offset
    )
    $
"#;

fn parse_two(bytes: &[u8], start: usize) -> Option<u32> {
    let first = *bytes.get(start)?;
    let second = *bytes.get(start + 1)?;
    if !first.is_ascii_digit() || !second.is_ascii_digit() {
        return None;
    }
    Some(u32::from(first - b'0') * 10 + u32::from(second - b'0'))
}

fn parse_four(bytes: &[u8], start: usize) -> Option<u32> {
    let high = parse_two(bytes, start)?;
    let low = parse_two(bytes, start + 2)?;
    Some(high * 100 + low)
}

fn is_leap_year(year: u32) -> bool {
    (year % 4 == 0 && year % 100 != 0) || year % 400 == 0
}

fn days_in_month(year: u32, month: u32) -> Option<u32> {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => Some(31),
        4 | 6 | 9 | 11 => Some(30),
        2 if is_leap_year(year) => Some(29),
        2 => Some(28),
        _ => None,
    }
}

fn validate_ascii(input: &[u8]) -> bool {
    // Python's `$` accepts one final newline. Preserve that exact regex edge.
    let bytes = input.strip_suffix(b"\n").unwrap_or(input);
    if bytes.len() < 20 {
        return false;
    }

    if bytes.get(4) != Some(&b'-')
        || bytes.get(7) != Some(&b'-')
        || bytes.get(10) != Some(&b'T')
        || bytes.get(13) != Some(&b':')
        || bytes.get(16) != Some(&b':')
    {
        return false;
    }

    let Some(year) = parse_four(bytes, 0) else {
        return false;
    };
    let Some(month) = parse_two(bytes, 5) else {
        return false;
    };
    let Some(day) = parse_two(bytes, 8) else {
        return false;
    };
    let Some(hour) = parse_two(bytes, 11) else {
        return false;
    };
    let Some(minute) = parse_two(bytes, 14) else {
        return false;
    };
    let Some(second) = parse_two(bytes, 17) else {
        return false;
    };

    if year == 0
        || hour > 23
        || minute > 59
        || second > 59
        || day == 0
        || day > days_in_month(year, month).unwrap_or(0)
    {
        return false;
    }

    let mut cursor = 19;
    if bytes.get(cursor) == Some(&b'.') {
        cursor += 1;
        let fraction_start = cursor;
        while bytes.get(cursor).is_some_and(u8::is_ascii_digit) {
            cursor += 1;
        }
        if cursor == fraction_start {
            return false;
        }
    }

    match bytes.get(cursor) {
        Some(b'Z') => cursor + 1 == bytes.len(),
        Some(b'+') | Some(b'-') => {
            let Some(offset_hour) = parse_two(bytes, cursor + 1) else {
                return false;
            };
            let Some(offset_minute) = parse_two(bytes, cursor + 4) else {
                return false;
            };
            bytes.get(cursor + 3) == Some(&b':')
                && offset_hour <= 23
                && offset_minute <= 59
                && cursor + 6 == bytes.len()
        }
        _ => false,
    }
}

/// Validates dates against RFC3339 datetime format.
/// Leap seconds are no supported.
#[pyfunction(name = "_native_validate_rfc3339", signature = (date_string))]
fn validate_rfc3339(py: Python<'_>, date_string: &Bound<'_, PyAny>) -> PyResult<bool> {
    if let Ok(value) = date_string.downcast::<PyString>() {
        return Ok(validate_ascii(value.to_string_lossy().as_bytes()));
    }

    // Delegate only the invalid-type boundary to the frozen Python regex so
    // TypeError classes and version-specific messages remain identical.
    let module = py.import("rfc3339_validator")?;
    module
        .getattr("RFC3339_REGEX")?
        .call_method1("match", (date_string,))?;
    unreachable!("a non-string argument must be rejected by a string regex")
}

#[pymodule]
fn _native(py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    let re = py.import("re")?;
    let calendar = py.import("calendar")?;
    let six = py.import("six")?;
    // Upstream exposes only re.ASCII as RFC3339_REGEX_FLAGS on Python 3.
    // re.VERBOSE is an implementation detail used to compile the public regex.
    // Keep the Python RegexFlag object instead of converting it to a Rust
    // integer, because its runtime type is observable by callers.
    let public_flags = re.getattr("ASCII")?;
    let verbose = re.getattr("VERBOSE")?;
    let compile_flags = verbose.call_method1("__or__", (&public_flags,))?;
    let regex = re.call_method1("compile", (RFC3339_PATTERN, compile_flags))?;

    module.add("__author__", "Nicolas Aimetti")?;
    module.add("__email__", "naimetti@yahoo.com.ar")?;
    module.add("__version__", "0.1.4")?;
    module.add("__replacement_version__", "0.1.0")?;
    module.add("re", re)?;
    module.add("calendar", calendar)?;
    module.add("six", six)?;
    module.add("RFC3339_REGEX_FLAGS", public_flags)?;
    module.add("RFC3339_REGEX", regex)?;
    module.add_function(wrap_pyfunction!(validate_rfc3339, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::validate_ascii;

    #[test]
    fn accepts_frozen_valid_examples() {
        assert!(validate_ascii(b"2020-02-29T23:59:59Z"));
        assert!(validate_ascii(b"2020-01-01T00:00:00.123+23:59"));
        assert!(validate_ascii(b"2020-01-01T00:00:00Z\n"));
    }

    #[test]
    fn rejects_frozen_invalid_examples() {
        assert!(!validate_ascii(b"0000-01-01T00:00:00Z"));
        assert!(!validate_ascii(b"2019-02-29T00:00:00Z"));
        assert!(!validate_ascii(b"2020-01-01t00:00:00z"));
        assert!(!validate_ascii(b"2020-01-01T00:00:60Z"));
        assert!(!validate_ascii(b"2020-01-01T00:00:00Z\n\n"));
    }
}

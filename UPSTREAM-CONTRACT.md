# Frozen upstream contract

## Identity

| Field | Frozen value |
|---|---|
| Distribution | `rfc3339-validator` |
| Import module | `rfc3339_validator` |
| Version | `0.1.4` |
| Repository | <https://github.com/naimetti/rfc3339-validator> |
| Tag / commit | `v0.1.4` / `5ebeb83a83ae5a65e610ffd90de36d30d7161aec` |
| License | MIT; local `LICENSE` SHA256 `5ba1a4f03626ccca6dcbf53a554545e4f776a335bfdaa233ec3bfe9bb7fac15d` |
| Runtime dependency | `six` |
| Python | `>=2.7`, excluding `3.0.*` through `3.4.*` |
| sdist | `rfc3339_validator-0.1.4.tar.gz`, SHA256 `138a2abdf93304ad60530167e51d2dfb9549521a836871b88d7f4695d0022f6b` |
| wheel | `rfc3339_validator-0.1.4-py2.py3-none-any.whl`, SHA256 `24f6ec1eda14ef823da9e36ec7113124b39c04d50a4d3d3a3c2859577e7791fa` |

Frozen local files:

- `upstream/oracle/rfc3339_validator.py`: SHA256 `c220cb9495da5215a53ab173f695060294df2d1042a9cbaaf0cc622bcba09d6e`
- `upstream/tests/test_rfc3339_validator.py`: SHA256 `478b821ea00f3b940e9d6ed77a7a831cf8a56e89b4712e289a5692ab62a39c13`

## Public and observable surface

- `validate_rfc3339(date_string)` with signature `(date_string)` and `bool` result for string inputs.
- `__author__`, `__email__`, `__version__`.
- `RFC3339_REGEX_FLAGS`: Python 3 value is `re.ASCII`; its runtime type must match the Oracle. Python 2 value is integer `0`.
- `RFC3339_REGEX`: `re.Pattern` on supported Python 3 runtimes; `.pattern` and `.flags` must equal the Oracle. `re.VERBOSE` is used only in its compiled flags and is not part of `RFC3339_REGEX_FLAGS`.
- Imported module attributes `calendar`, `re`, and `six` remain visible and identify the same imported module objects.
- No console script is provided. There is no package `__main__` API; executing the single module with `python -m rfc3339_validator` has no output or command behavior.

## Behavioral boundaries

- Exact ASCII RFC3339 shape, uppercase `T` and `Z`, optional fractional seconds, and numeric UTC offsets.
- Calendar-valid year/month/day; year zero is rejected; leap seconds are rejected.
- Python regex `$` accepts one trailing newline, and the replacement must preserve this edge.
- Unicode digits are rejected under Python 3 because the regex carries `re.ASCII`.
- Non-string inputs raise the same exception class and message as the Oracle regex on each runtime.
- Regex globals, metadata, function signature, result type, module globals, and import/entry-point behavior are part of compatibility, not implementation details.

## Complete upstream suite

The frozen suite is exactly the unmodified `upstream/tests/test_rfc3339_validator.py`:

- `test_valid_dates` (skipped only by the upstream marker on Python 2);
- `test_against_legacy` with `max_examples=1500`;
- `test_with_unicode` with the upstream example and Hypothesis settings.

No test selection, custom xfail, deletion, or mutation is allowed.

import importlib.util
from importlib import metadata
import inspect
from pathlib import Path
import re
import subprocess
import sys

import pytest

import rfc3339_validator as candidate


def load_oracle():
    path = Path(__file__).parents[1] / "upstream" / "oracle" / "rfc3339_validator.py"
    spec = importlib.util.spec_from_file_location("frozen_rfc3339_oracle", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2020-02-29T23:59:59Z", True),
        ("2020-01-01T00:00:00.123+23:59", True),
        ("2020-01-01T00:00:00Z\n", True),
        ("0000-01-01T00:00:00Z", False),
        ("2019-02-29T00:00:00Z", False),
        ("2020-01-01t00:00:00z", False),
        ("２０２０-01-01T00:00:00Z", False),
    ],
)
def test_frozen_values(value, expected):
    assert candidate.validate_rfc3339(value) is expected


def test_public_surface_and_signature():
    oracle = load_oracle()
    assert candidate.__doc__ is oracle.__doc__ is None
    assert not hasattr(candidate, "__all__")
    assert str(inspect.signature(candidate.validate_rfc3339)) == "(date_string)"
    assert candidate.validate_rfc3339.__doc__ == oracle.validate_rfc3339.__doc__
    assert candidate.validate_rfc3339.__annotations__ == oracle.validate_rfc3339.__annotations__
    assert candidate.validate_rfc3339.__defaults__ == oracle.validate_rfc3339.__defaults__
    assert candidate.validate_rfc3339.__name__ == oracle.validate_rfc3339.__name__
    assert candidate.validate_rfc3339.__qualname__ == oracle.validate_rfc3339.__qualname__
    assert candidate.__version__ == "0.1.4"
    assert candidate.__replacement_version__ == "0.1.0"
    assert candidate.RFC3339_REGEX_FLAGS == re.ASCII
    assert type(candidate.RFC3339_REGEX_FLAGS) is type(oracle.RFC3339_REGEX_FLAGS)
    assert isinstance(candidate.RFC3339_REGEX, re.Pattern)
    assert candidate.RFC3339_REGEX.pattern == oracle.RFC3339_REGEX.pattern
    assert candidate.RFC3339_REGEX.flags == oracle.RFC3339_REGEX.flags
    for name in ("calendar", "re", "six"):
        assert getattr(candidate, name) is getattr(oracle, name)


def test_star_import_matches_oracle_without_dunder_exports():
    oracle = load_oracle()
    namespace = {}
    exec("from rfc3339_validator import *", namespace)
    actual = {name for name in namespace if name != "__builtins__"}
    expected = {name for name in vars(oracle) if not name.startswith("_")}
    assert actual == expected


def test_no_cli_and_silent_module_execution():
    distribution = metadata.distribution("fast-rfc3339-validator-rs")
    assert not [entry for entry in distribution.entry_points if entry.group == "console_scripts"]
    completed = subprocess.run(
        [sys.executable, "-m", "rfc3339_validator"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""


@pytest.mark.parametrize("value", [None, 1, b"2020-01-01T00:00:00Z"])
def test_invalid_type_raises_type_error(value):
    with pytest.raises(TypeError):
        candidate.validate_rfc3339(value)

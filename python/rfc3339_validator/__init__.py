# -*- coding: utf-8 -*-

from rfc3339_validator._native import (
    RFC3339_REGEX,
    RFC3339_REGEX_FLAGS,
    __author__,
    __email__,
    __replacement_version__,
    __version__,
    _native_validate_rfc3339,
    calendar,
    re,
    six,
)


def validate_rfc3339(date_string):
    """
    Validates dates against RFC3339 datetime format
    Leap seconds are no supported.
    """
    return _native_validate_rfc3339(date_string)

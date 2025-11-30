# tests/test_date_utils.py
import os
import sys
import datetime as dt
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import normalize_iso_date


def test_normalize_valid_iso_string():
    d = normalize_iso_date("2025-01-10")
    assert isinstance(d, dt.date)
    assert d == dt.date(2025, 1, 10)


def test_normalize_invalid_month():
    with pytest.raises(ValueError) as exc:
        normalize_iso_date("2025-13-01")
    assert "Invalid date format" in str(exc.value)


def test_normalize_invalid_string():
    with pytest.raises(ValueError):
        normalize_iso_date("not-a-date")


def test_normalize_already_date():
    original = dt.date(2025, 1, 10)
    result = normalize_iso_date(original)
    # same value
    assert result == original


def test_normalize_none_raises():
    # Your validator would treat this as "invalid format"
    with pytest.raises(ValueError):
        normalize_iso_date(None)

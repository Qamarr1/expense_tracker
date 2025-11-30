# tests/test_expense_classification.py
from decimal import Decimal

from utils import classify_expense


def dec(x):
    return Decimal(str(x))


def test_normal_expense_no_flags():
    flags = classify_expense(amount=dec(50), balance=dec(1000), large_threshold=dec(500))
    assert flags == []


def test_large_expense_within_balance():
    flags = classify_expense(amount=dec(600), balance=dec(2000), large_threshold=dec(500))
    assert "large_expense" in flags
    assert "exceeds_balance" not in flags


def test_exceeds_balance_not_large():
    flags = classify_expense(amount=dec(900), balance=dec(800), large_threshold=dec(1000))
    assert "exceeds_balance" in flags
    assert "large_expense" not in flags


def test_large_and_exceeds_balance():
    flags = classify_expense(amount=dec(1500), balance=dec(1000), large_threshold=dec(500))
    assert "exceeds_balance" in flags
    assert "large_expense" in flags


def test_no_balance_only_large_threshold():
    flags = classify_expense(amount=dec(600), balance=None, large_threshold=dec(500))
    assert "large_expense" in flags
    assert "exceeds_balance" not in flags


def test_exactly_equal_to_threshold_is_large():
    flags = classify_expense(amount=dec(500), balance=dec(1000), large_threshold=dec(500))
    assert "large_expense" in flags

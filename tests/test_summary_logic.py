from decimal import Decimal
import pytest

from utils import compute_summary



def test_summary_empty():
    result = compute_summary([], [])
    assert result["total_income"] == 0.0
    assert result["total_expenses"] == 0.0
    assert result["balance"] == 0.0


def test_summary_only_income():
    incomes = [Decimal("100"), Decimal("50.55")]
    result = compute_summary(incomes, [])
    assert result["total_income"] == 150.55
    assert result["total_expenses"] == 0.0
    assert result["balance"] == 150.55


def test_summary_only_expenses_negative_balance():
    expenses = [Decimal("40"), Decimal("10.5")]
    result = compute_summary([], expenses)
    assert result["total_income"] == 0.0
    assert result["total_expenses"] == 50.5
    # allowed to be negative
    assert result["balance"] == -50.5


def test_summary_mixed_income_and_expenses():
    incomes = [Decimal("100"), Decimal("20.12")]
    expenses = [Decimal("50")]
    result = compute_summary(incomes, expenses)
    assert result["total_income"] == 120.12
    assert result["total_expenses"] == 50.0
    assert result["balance"] == 70.12


def test_summary_large_and_small_values():
    incomes = [Decimal("10000000.12")]
    expenses = [Decimal("0.015")]
    result = compute_summary(incomes, expenses)

    # 1) totals should reflect sums (rounded to 2dp)
    assert result["total_income"] == 10_000_000.12
    assert result["total_expenses"] == 0.01  # round(0.015, 2) -> 0.01

    # 2) balance should be income - expenses
    expected_balance = round(10000000.12 - 0.015, 2)

    #  approx just in case of tiny float artifacts
    assert result["balance"] == pytest.approx(expected_balance, rel=1e-9)

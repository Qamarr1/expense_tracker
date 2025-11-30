# tests/test_utils.py

import os
import sys
from decimal import Decimal
import datetime as dt

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils import compute_summary
from models import Transaction


def make_tx(amount, type_):
    return Transaction(
        id=None,
        name="X",
        amount=Decimal(str(amount)),
        date=dt.date(2025, 1, 1),
        note=None,
        type=type_,
        category_id=None,
    )


def test_summary_empty():
    result = compute_summary([])
    assert result["income_total"] == 0.0
    assert result["expense_total"] == 0.0
    assert result["balance"] == 0.0


def test_summary_only_income():
    txs = [make_tx(100, "income"), make_tx(50.55, "income")]
    result = compute_summary(txs)
    assert result["income_total"] == 150.55
    assert result["expense_total"] == 0.0
    assert result["balance"] == 150.55


def test_summary_only_expenses():
    txs = [make_tx(40, "expense"), make_tx(10.5, "expense")]
    result = compute_summary(txs)
    assert result["income_total"] == 0.0
    assert result["expense_total"] == 50.5
    assert result["balance"] == -50.5


def test_summary_mixed():
    txs = [
        make_tx(100, "income"),
        make_tx(20.12, "income"),
        make_tx(50, "expense"),
    ]
    result = compute_summary(txs)
    assert result["income_total"] == 120.12
    assert result["expense_total"] == 50.0
    assert result["balance"] == 70.12


def test_summary_large_small_values():
    txs = [
        make_tx(10_000_000.12, "income"),
        make_tx(0.015, "expense"),
    ]
    result = compute_summary(txs)

    assert result["income_total"] == 10_000_000.12
    assert result["expense_total"] == 0.02  # 0.015 rounds up
    assert result["balance"] == result["income_total"] - result["expense_total"]




# tests/test_filter_transactions.py
import datetime as dt
from decimal import Decimal

from models import Transaction
from utils import filter_transactions


def make_tx(name, amount, type_, date_str, note=None):
    year, month, day = map(int, date_str.split("-"))
    return Transaction(
        id=None,
        name=name,
        amount=Decimal(str(amount)),
        date=dt.date(year, month, day),
        note=note,
        type=type_,
        category_id=None,
    )


def base_transactions():
    return [
        make_tx("Salary", 1000, "income", "2025-01-01", "monthly salary"),
        make_tx("Bonus", 500, "income", "2025-01-15", "yearly bonus"),
        make_tx("Rent", 700, "expense", "2025-01-05", "apartment rent"),
        make_tx("Groceries", 120, "expense", "2025-01-20", "food shopping"),
        make_tx("Old rent", 650, "expense", "2024-12-20", "previous month rent"),
    ]


def test_filter_no_filters_returns_all():
    txs = base_transactions()
    result = filter_transactions(txs)
    assert len(result) == len(txs)


def test_filter_by_type_income_only():
    txs = base_transactions()
    result = filter_transactions(txs, tx_type="income")
    assert all(t.type == "income" for t in result)
    assert {t.name for t in result} == {"Salary", "Bonus"}


def test_filter_by_type_expense_only():
    txs = base_transactions()
    result = filter_transactions(txs, tx_type="expense")
    assert all(t.type == "expense" for t in result)
    assert {t.name for t in result} == {"Rent", "Groceries", "Old rent"}


def test_filter_by_date_range_inclusive():
    txs = base_transactions()
    date_from = dt.date(2025, 1, 5)
    date_to = dt.date(2025, 1, 15)
    result = filter_transactions(txs, date_from=date_from, date_to=date_to)
    # dates between 5th and 15th inclusive
    names = {t.name for t in result}
    assert names == {"Rent", "Bonus"}


def test_filter_by_query_name_or_note_case_insensitive():
    txs = base_transactions()
    # query should match "rent" in name or note
    result = filter_transactions(txs, query="RENt")
    names = {t.name for t in result}
    assert "Rent" in names or "Old rent" in names
    assert any("rent" in (t.name or "").lower() or "rent" in (t.note or "").lower() for t in result)


def test_filter_combined_type_date_and_query():
    txs = base_transactions()
    date_from = dt.date(2025, 1, 1)
    date_to = dt.date(2025, 1, 31)
    result = filter_transactions(
        txs,
        date_from=date_from,
        date_to=date_to,
        query="rent",
        tx_type="expense",
    )
    # should only pick the January "Rent", not "Old rent" from December
    assert len(result) == 1
    assert result[0].name == "Rent"

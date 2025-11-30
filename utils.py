"""Utility functions for summary computation, dates, and classifications."""
import datetime as dt
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional

from models import Transaction


def _to_float_sum(values: Iterable[Decimal | float | int]) -> float:
    """
    Helper: safely sum Decimals / floats / ints and return a float.
    Empty input => 0.0
    """
    total = sum(values) if values else 0
    return float(total)


def compute_summary(
    incomes: Iterable[Decimal | float | int],
    expenses: Iterable[Decimal | float | int],
) -> Dict[str, float]:
    """
    Compute simple totals for income & expenses and overall balance.

    Returns a dict with stable keys used by:
      - /api/stats/summary
      - tests (including Postgres API tests)
      - the frontend dashboard
    """
    total_income = _to_float_sum(list(incomes))
    total_expenses = _to_float_sum(list(expenses))
    balance = total_income - total_expenses

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "balance": round(balance, 2),
    }


def normalize_iso_date(value: Any) -> dt.date:
    """Normalize a value to a date or raise a ValueError."""
    if isinstance(value, dt.date):
        return value

    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except Exception:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

    raise ValueError("Invalid date format. Expected YYYY-MM-DD.")


def filter_transactions(
    transactions: Iterable[Transaction],
    date_from: Optional[dt.date] = None,
    date_to: Optional[dt.date] = None,
    query: Optional[str] = None,
    tx_type: Optional[str] = None,
) -> list[Transaction]:
    """Filter transactions by date range, text query, and type."""
    q = (query or "").strip().lower()
    results: list[Transaction] = []

    for t in transactions:

        if tx_type and t.type != tx_type:
            continue

        if isinstance(t.date, dt.date):
            if date_from and t.date < date_from:
                continue
            if date_to and t.date > date_to:
                continue

        if q:
            name = (t.name or "").lower()
            note = (t.note or "").lower()
            if q not in name and q not in note:
                continue

        results.append(t)

    return results


def classify_expense(
    amount: Decimal,
    balance: Optional[Decimal],
    large_threshold: Decimal = Decimal("500"),
) -> list[str]:
    """Return flags for expenses that exceed balance or a large threshold."""
    flags: list[str] = []

    if balance is not None and amount > balance:
        flags.append("exceeds_balance")

    if amount >= large_threshold:
        flags.append("large_expense")

    return flags

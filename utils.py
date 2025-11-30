"""Utility functions for summary computation, dates, and classifications."""
import datetime as dt
from decimal import Decimal,ROUND_HALF_UP
from typing import Any, Iterable, Optional

from models import Transaction

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from models import Transaction


def _round_money(dec: Decimal) -> float:
    """Round a Decimal to 2 decimal places with HALF_UP (normal money rounding)."""
    return float(dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def compute_summary(transactions: Iterable[Transaction]) -> dict[str, float]:
    """
    Aggregate totals for income, expenses, and balance.

    Returns keys that the tests expect:
      - total_income
      - total_expenses
      - balance
    """
    income_total_dec = Decimal("0")
    expense_total_dec = Decimal("0")

    for t in transactions:
        if t.type == "income":
            income_total_dec += Decimal(t.amount)
        elif t.type == "expense":
            expense_total_dec += Decimal(t.amount)

    # money-safe rounding
    total_income = _round_money(income_total_dec)
    total_expenses = _round_money(expense_total_dec)

    balance = total_income - total_expenses
    balance_rounded = _round_money(Decimal(str(balance)))

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": balance_rounded,
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

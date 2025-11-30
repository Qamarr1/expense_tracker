import datetime as dt
import pytest
from pydantic import ValidationError
from schemas import TransactionUpdate , ExpenseCreate
from decimal import Decimal

def test_expense_create_trims_name_and_note():
    payload = ExpenseCreate(
        name="  Taxi ride  ",
        amount=Decimal("5"),
        date="2025-01-01",  # string on purpose, validator will handle
        note="  Airport  ",
        category_id=1,
    )
    assert payload.name == "Taxi ride"
    assert payload.note == "Airport"


def test_expense_create_too_long_name_rejected():
    long_name = "X" * 300  # > NAME_MAX_LEN (100)
    with pytest.raises(ValidationError):
        ExpenseCreate(
            name=long_name,
            amount=Decimal("10"),
            date="2025-01-01",
            category_id=1,
        )

def test_transaction_update_parse_date_from_valid_string():
    # Arrange
    payload = {"date": "2025-01-15"}

    # Act
    obj = TransactionUpdate(**payload)

    # Assert
    assert isinstance(obj.date, dt.date)
    assert obj.date == dt.date(2025, 1, 15)

def test_transaction_update_keeps_date_instance():
    # Arrange
    d = dt.date(2025, 2, 3)
    payload = {"date": d}

    # Act
    obj = TransactionUpdate(**payload)

    # Assert
    assert obj.date is d
def test_transaction_update_rejects_invalid_date_format():
    # Arrange
    payload = {"date": "03/02/2025"}  # wrong format

    # Act + Assert
    with pytest.raises(ValidationError) as exc_info:
        TransactionUpdate(**payload)

    # Optional: check error message text
    msg = str(exc_info.value)
    assert "Invalid date format. Expected YYYY-MM-DD." in msg

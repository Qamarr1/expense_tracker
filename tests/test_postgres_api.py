# tests/test_postgres_api.py
import os

import pytest
from fastapi.testclient import TestClient

from main import app

POSTGRES_URL = os.getenv("POSTGRES_TEST_URL")

client = TestClient(app)


@pytest.mark.integration
@pytest.mark.skipif(
    not POSTGRES_URL,
    reason="POSTGRES_TEST_URL not set, skipping Postgres API integration tests.",
)
def test_postgres_health_and_categories():
    """
    Check that the API is up and Postgres-backed categories can be listed.
    No assumptions about specific seeded names.
    """
    r = client.get("/health")
    assert r.status_code == 200

    r_cat = client.get("/api/categories")
    assert r_cat.status_code == 200

    cats = r_cat.json()
    assert isinstance(cats, list)
    # At least one category should exist (created either by app startup
    # or by other tests).
    assert len(cats) >= 1

    first = cats[0]
    assert "id" in first
    assert "name" in first


@pytest.mark.integration
@pytest.mark.skipif(
    not POSTGRES_URL,
    reason="POSTGRES_TEST_URL not set, skipping Postgres API integration tests.",
)
def test_postgres_income_expense_flow():
    """
    End-to-end Postgres flow via the HTTP API:

    - Fetch categories
    - Create an income
    - Create an expense using a real category
    - Confirm /api/stats/summary reflects at least those amounts
    """
    # 1) Get any real category
    r_cat = client.get("/api/categories")
    assert r_cat.status_code == 200
    cats = r_cat.json()
    assert cats
    cat_id = cats[0]["id"]

    # 2) Create an income
    income_amount = 123.45
    r_inc = client.post(
        "/api/income",
        json={
            "name": "PG Salary Test",
            "amount": income_amount,
            "date": "2025-01-01",
            "note": "postgres-income",
        },
    )
    assert r_inc.status_code == 201
    inc_row = r_inc.json()
    assert inc_row["type"] == "income"

    # 3) Create an expense
    expense_amount = 45.67
    r_exp = client.post(
        "/api/expenses",
        json={
            "name": "PG Expense Test",
            "amount": expense_amount,
            "date": "2025-01-02",
            "note": "postgres-expense",
            "category_id": cat_id,
        },
    )
    assert r_exp.status_code == 201
    exp_row = r_exp.json()
    assert exp_row["type"] == "expense"
    assert exp_row["category_id"] == cat_id

    # 4) Check summary reflects at *least* those amounts
    r_summary = client.get("/api/stats/summary")
    assert r_summary.status_code == 200
    summary = r_summary.json()

    total_income = summary["total_income"]
    total_expenses = summary["total_expenses"]
    balance = summary["balance"]

    # These should be >= what we just added (other data may exist too)
    assert total_income >= income_amount
    assert total_expenses >= expense_amount
    # Balance is income - expenses, allow for other rows too
    assert abs(balance) <= max(total_income, total_expenses)


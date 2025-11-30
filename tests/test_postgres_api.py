# tests/test_postgres_api.py

import os
import pytest

from sqlmodel import SQLModel
from fastapi.testclient import TestClient

# Only run these tests if POSTGRES_TEST_URL is set 
POSTGRES_URL = os.getenv("POSTGRES_TEST_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="POSTGRES_TEST_URL not set, skipping Postgres API integration tests.",
)

# set DATABASE_URL before importing main.py
os.environ["DATABASE_URL"] = POSTGRES_URL

from main import app, engine, DEFAULT_CATEGORIES  # noqa: E402


# Create tables in the Postgres DB (idempotent)
SQLModel.metadata.create_all(engine)

client = TestClient(app)


def test_postgres_health_and_categories():
    """
    Full-stack check:

    - FastAPI app runs against Postgres
    - /health works
    - /api/categories reads from Postgres and has the default seeded categories
    """
    # /health
    r_health = client.get("/health")
    assert r_health.status_code == 200
    data = r_health.json()
    assert data["status"] == "ok"

    # /api/categories
    r_cat = client.get("/api/categories")
    assert r_cat.status_code == 200
    cats = r_cat.json()
    assert isinstance(cats, list)
    # Should contain at least all DEFAULT_CATEGORIES
    names = {c["name"] for c in cats}
    for name in DEFAULT_CATEGORIES:
        assert name in names


def test_postgres_income_expense_flow():
    """
    End-to-end Postgres flow:

    - Pick a real category from Postgres
    - Create an income and an expense via API
    - Call /api/stats/summary and check they are reflected in totals
    """
    # Get any category (e.g., "Food & Dining")
    r_cat = client.get("/api/categories")
    assert r_cat.status_code == 200
    cats = r_cat.json()
    assert cats

    # Try to find "Food & Dining"; fallback to first
    cat_id = None
    for c in cats:
        if c["name"] == "Food & Dining":
            cat_id = c["id"]
            break
    if cat_id is None:
        cat_id = cats[0]["id"]

    # Create an income
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

    # Create an expense
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

    # Check summary reflects at least these amounts
    r_summary = client.get("/api/stats/summary")
    assert r_summary.status_code == 200
    summary = r_summary.json()

    # Because DB may already have data, we check ">= our amounts"
    assert summary["income_total"] >= income_amount
    assert summary["expense_total"] >= expense_amount
    # Balance should be income - expenses (already validated in unit tests)

import os
import sys
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

# import main.py & setup in-memory DB like  other tests

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import app, get_session  # noqa: E402


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

SQLModel.metadata.create_all(test_engine)


def override_get_session():
    with Session(test_engine) as session:
        yield session


app.dependency_overrides[get_session] = override_get_session

client = TestClient(app)


# helpers 
def create_category(name: str = "FlowCat") -> int:
    resp = client.post("/api/categories", json={"name": name})
    # first time: 201, later: 400 (already exists) – accept both
    assert resp.status_code in (201, 400)

    resp_list = client.get("/api/categories")
    assert resp_list.status_code == 200
    cats = resp_list.json()
    for c in cats:
        if c["name"] == name:
            return c["id"]
    raise AssertionError("Category not found after creation")


def create_income(name: str, amount: float, date: str = "2025-01-01"):
    resp = client.post(
        "/api/income",
        json={
            "name": name,
            "amount": amount,
            "date": date,
            "note": None,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def create_expense(
    name: str,
    amount: float,
    category_id: int,
    date: str = "2025-01-01",
):
    resp = client.post(
        "/api/expenses",
        json={
            "name": name,
            "amount": amount,
            "date": date,
            "note": None,
            "category_id": category_id,
        },
    )
    assert resp.status_code == 201
    return resp.json()


# TEST 1: /api/stats/summary end-to-end 
def test_summary_endpoint_with_real_data():
    """
    Integration test: use the real API endpoints to create data,
    then verify that /api/stats/summary returns correct totals.
    """
    # Arrange: create some incomes and expenses
    inc1 = create_income("Salary", 1000.50, "2025-01-01")
    inc2 = create_income("Freelance", 200.25, "2025-01-05")

    cat_id = create_category("SummaryCat")
    exp1 = create_expense("Groceries", 100.10, cat_id, "2025-01-02")
    exp2 = create_expense("Taxi", 50.00, cat_id, "2025-01-03")

    # Act: call summary endpoint
    resp = client.get("/api/stats/summary")
    assert resp.status_code == 200
    data = resp.json()

    # Assert: totals and balance match our created data
    # total_income = 1000.50 + 200.25 = 1200.75
    # total_expenses = 100.10 + 50.00 = 150.10
    # balance = 1050.65
    assert round(float(data["total_income"]), 2) == round(1000.50 + 200.25, 2)
    assert round(float(data["total_expenses"]), 2) == round(100.10 + 50.00, 2)
    assert round(float(data["balance"]), 2) == round(
        (1000.50 + 200.25) - (100.10 + 50.00), 2
    )


# TEST 2: category deletion rule 


def test_category_cannot_be_deleted_if_in_use():
    """
    Integration test: business rule that categories in use cannot be deleted.
    """
    cat_id = create_category("ProtectedCat")

    # Create an expense that uses this category
    _exp = create_expense("Rent", 500.0, cat_id, "2025-01-01")

    # Try to delete the category
    resp_del = client.delete(f"/api/categories/{cat_id}")

    # Should be blocked with 400
    assert resp_del.status_code == 400
    body = resp_del.json()
    assert "detail" in body
    assert "in use" in body["detail"].lower()

    # And category should still appear in list
    resp_list = client.get("/api/categories")
    assert resp_list.status_code == 200
    ids = [c["id"] for c in resp_list.json()]
    assert cat_id in ids


# TEST 3: /metrics exposed and Prometheus-ish 


def test_metrics_endpoint_exposed():
    """
    Integration test: the Prometheus /metrics endpoint is available
    and returns something that looks like metrics text.
    """
    resp = client.get("/metrics")
    assert resp.status_code == 200

    text = resp.text
    # Prometheus text format usually starts with '# HELP' / '# TYPE'
    assert "# HELP" in text or "# TYPE" in text

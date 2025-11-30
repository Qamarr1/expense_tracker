# ---------- helper: create a category ----------
def create_test_category(client, name="TestCat"):
    res = client.post("/api/categories", json={"name": name})
    if res.status_code not in (201, 400):
        raise RuntimeError(f"Unexpected status creating category: {res.status_code}")
    res_list = client.get("/api/categories")
    cats = res_list.json()
    for c in cats:
        if c["name"] == name:
            return c["id"]
    raise RuntimeError(f"Category {name} not found after creation")


# ---------- tests ----------
def test_create_expense(client):
    cat_id = create_test_category(client)

    payload = {
        "name": "Test Expense",
        "amount": 100.00,
        "date": "2025-01-01",
        "category_id": cat_id,
        "note": "for testing",
    }
    res = client.post("/api/expenses", json=payload)
    assert res.status_code == 201

    data = res.json()
    assert data["name"] == "Test Expense"
    assert float(data["amount"]) == 100.00
    assert data["type"] == "expense"
    assert data["category_id"] == cat_id


def test_list_expenses(client):
    res = client.get("/api/expenses")
    assert res.status_code == 200

    data = res.json()
    assert isinstance(data, list)


def test_create_expense_invalid_category(client):
    payload = {
        "name": "Bad expense",
        "amount": 10.0,
        "date": "2025-01-01",
        "category_id": 999999,
        "note": None,
    }
    res = client.post("/api/expenses", json=payload)
    assert res.status_code == 400
    assert "Category not found" in res.text


def test_update_expense(client):
    base_cat_id = create_test_category(client, "BaseCat")
    res_create = client.post(
        "/api/expenses",
        json={
            "name": "Original Expense",
            "amount": 150.0,
            "date": "2025-01-02",
            "category_id": base_cat_id,
        },
    )
    assert res_create.status_code == 201
    exp_id = res_create.json()["id"]

    new_cat_id = create_test_category(client, "AnotherCat")

    res_upd = client.patch(
        f"/api/expenses/{exp_id}",
        json={
            "name": "Updated Expense",
            "amount": 250.0,
            "category_id": new_cat_id,
        },
    )
    assert res_upd.status_code == 200
    data = res_upd.json()
    assert data["name"] == "Updated Expense"
    assert float(data["amount"]) == 250.0
    assert data["category_id"] == new_cat_id


def test_update_expense_invalid_category(client):
    res_cat = client.post("/api/categories", json={"name": "Food"})
    assert res_cat.status_code in (201, 400)
    cats = client.get("/api/categories").json()
    cat_id = next(c["id"] for c in cats if c["name"] == "Food")

    res_exp = client.post(
        "/api/expenses",
        json={
            "name": "Dinner",
            "amount": 20.0,
            "date": "2025-01-10",
            "category_id": cat_id,
        },
    )
    assert res_exp.status_code == 201
    exp = res_exp.json()

    res = client.patch(f"/api/expenses/{exp['id']}", json={"category_id": 999999})
    assert res.status_code == 400
    assert "Category not found" in res.text


def test_delete_expense(client):
    cat_id = create_test_category(client, "DeleteCat")

    # create new expense
    res_create = client.post(
        "/api/expenses",
        json={
            "name": "To Delete Expense",
            "amount": 75.0,
            "date": "2025-01-03",
            "category_id": cat_id,
            "note": None,
        },
    )
    assert res_create.status_code == 201
    exp_id = res_create.json()["id"]

    # delete
    res_del = client.delete(f"/api/expenses/{exp_id}")
    assert res_del.status_code == 204

    # ensure it's gone
    res_list = client.get("/api/expenses")
    ids = [row["id"] for row in res_list.json()]
    assert exp_id not in ids


def test_update_expense_only_note_preserves_other_fields(client):
    # 1) Create a category first (so category_id is valid)
    cat_id = create_test_category(client, "Food")

    # 2) Create an expense
    resp_create = client.post(
        "/api/expenses",
        json={
            "name": "Nobu dinner",
            "amount": 100.50,
            "date": "2025-01-10",
            "note": "Birthday",
            "category_id": cat_id,
        },
    )
    assert resp_create.status_code == 201
    original = resp_create.json()

    # 3) PATCH only the note
    resp_patch = client.patch(
        f"/api/expenses/{original['id']}",
        json={"note": "Updated note"},
    )
    assert resp_patch.status_code == 200
    data = resp_patch.json()

    # 4) Note changed
    assert data["note"] == "Updated note"

    # 5) Everything else stayed the same
    assert data["name"] == original["name"]
    assert data["amount"] == original["amount"]
    assert data["date"] == original["date"]
    assert data["category_id"] == original["category_id"]


def test_create_expense_negative_amount(client):
    cat_id = create_test_category(client, "NegCat")
    res = client.post(
        "/api/expenses",
        json={
            "name": "Bad expense",
            "amount": -10.0,
            "date": "2025-01-01",
            "category_id": cat_id,
        },
    )
    assert res.status_code in (400, 422)


def test_update_expense_not_found(client):
    res = client.patch("/api/expenses/999999", json={"name": "Nope"})
    assert res.status_code == 404

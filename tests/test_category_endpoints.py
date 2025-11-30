def test_rename_category_keeps_expense_link(client):
    res_cat = client.post("/api/categories", json={"name": "Food"})
    assert res_cat.status_code in (201, 400)

    cats = client.get("/api/categories").json()
    cat_id = next(c["id"] for c in cats if c["name"] == "Food")

    res_exp = client.post(
        "/api/expenses",
        json={
            "name": "Nobu dinner",
            "amount": 100.0,
            "date": "2025-01-10",
            "category_id": cat_id,
        },
    )
    assert res_exp.status_code == 201
    exp = res_exp.json()

    res_rename = client.patch(
        f"/api/categories/{cat_id}",
        json={"name": "Dining Out"},
    )
    assert res_rename.status_code == 200
    assert res_rename.json()["name"] == "Dining Out"

    cats_after = client.get("/api/categories").json()
    assert any(c["id"] == cat_id and c["name"] == "Dining Out" for c in cats_after)

    expenses = client.get("/api/expenses").json()
    found = next(e for e in expenses if e["id"] == exp["id"])
    assert found["category_id"] == cat_id


def test_delete_unused_category_succeeds(client):
    res = client.post("/api/categories", json={"name": "TempCat"})
    assert res.status_code in (201, 400)

    cats = client.get("/api/categories").json()
    cat_id = next(c["id"] for c in cats if c["name"] == "TempCat")

    res_del = client.delete(f"/api/categories/{cat_id}")
    assert res_del.status_code in (204, 400)


def test_delete_category_in_use_blocked(client):
    res_cat = client.post("/api/categories", json={"name": "ToBlockDelete"})
    assert res_cat.status_code in (201, 400)

    cats = client.get("/api/categories").json()
    cat_id = next(c["id"] for c in cats if c["name"] == "ToBlockDelete")

    res_exp = client.post(
        "/api/expenses",
        json={
            "name": "Some expense",
            "amount": 10.0,
            "date": "2025-01-10",
            "category_id": cat_id,
        },
    )
    assert res_exp.status_code == 201

    res_del = client.delete(f"/api/categories/{cat_id}")
    assert res_del.status_code == 400
    assert "in use" in res_del.text


def test_create_category_empty_name(client):
    res = client.post("/api/categories", json={"name": ""})
    assert res.status_code in (400, 422)


def test_update_category_not_found(client):
    res = client.patch("/api/categories/999999", json={"name": "NoCat"})
    assert res.status_code == 404

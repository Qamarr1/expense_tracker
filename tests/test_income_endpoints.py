# ---------- tests ----------
def test_create_income(client):
    payload = {
        "name": "Test Salary",
        "amount": 1200.50,
        "date": "2025-01-01",
        "note": "test note",
    }
    res = client.post("/api/income", json=payload)
    assert res.status_code == 201

    data = res.json()
    assert data["name"] == "Test Salary"
    assert float(data["amount"]) == 1200.50
    assert data["type"] == "income"


def test_list_income(client):
    client.post(
        "/api/income",
        json={
            "name": "Seed",
            "amount": 10.0,
            "date": "2025-01-01",
        },
    )
    res = client.get("/api/income")
    assert res.status_code == 200

    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_update_income(client):
    res_create = client.post(
        "/api/income",
        json={
            "name": "To Update",
            "amount": 100.0,
            "date": "2025-01-01",
        },
    )
    assert res_create.status_code == 201
    income_id = res_create.json()["id"]

    # update name + amount
    res_update = client.patch(
        f"/api/income/{income_id}",
        json={"name": "Updated Income", "amount": 2000.00},
    )
    assert res_update.status_code == 200
    updated = res_update.json()
    assert updated["name"] == "Updated Income"
    assert float(updated["amount"]) == 2000.00


def test_delete_income(client):
    # create one to delete
    res_create = client.post(
        "/api/income",
        json={
            "name": "To Delete",
            "amount": 50.0,
            "date": "2025-01-02",
            "note": None,
        },
    )
    assert res_create.status_code == 201
    income_id = res_create.json()["id"]

    # delete it
    res_del = client.delete(f"/api/income/{income_id}")
    assert res_del.status_code == 204

    # confirm gone
    res_list = client.get("/api/income")
    ids = [row["id"] for row in res_list.json()]
    assert income_id not in ids


def test_create_income_invalid_amount(client):
    res = client.post(
        "/api/income",
        json={
            "name": "Bad Income",
            "amount": -5,
            "date": "2025-01-01",
        },
    )
    assert res.status_code in (400, 422)


def test_update_income_not_found(client):
    res = client.patch("/api/income/999999", json={"name": "Nope"})
    assert res.status_code == 404

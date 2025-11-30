def test_health_status(client):
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert data["app"] == "expense-tracker"

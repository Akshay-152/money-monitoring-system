import json
from backend.api.app import create_app


def test_manual_transaction_and_classification(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    client = app.test_client()
    response = client.post("/api/transactions", json={"amount": -50, "description": "Lunch", "category": "Food", "payment_mode": "UPI"})
    assert response.status_code == 201
    transaction = response.get_json()
    assert client.get("/api/summary").get_json()["expense"] == 50
    assert client.post("/api/classify", json={"id": transaction["id"], "category": "Other"}).status_code == 200


def test_validation_rejects_unknown_fields(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    response = app.test_client().post("/api/transactions", json={"amount": 4, "unexpected": True})
    assert response.status_code == 400

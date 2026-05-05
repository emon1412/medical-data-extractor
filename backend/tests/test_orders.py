import uuid


def _payload(**overrides):
    base = {
        "patient_first_name": "Jane",
        "patient_last_name": "Doe",
        "patient_dob": "1990-01-15",
        "status": "pending",
        "notes": "First visit",
    }
    base.update(overrides)
    return base


def test_create_and_get_order(client):
    r = client.post("/api/v1/orders", json=_payload())
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["id"]
    assert created["patient_first_name"] == "Jane"
    assert created["status"] == "pending"

    r2 = client.get(f"/api/v1/orders/{created['id']}")
    assert r2.status_code == 200
    assert r2.json()["id"] == created["id"]


def test_list_with_search_and_status(client):
    client.post("/api/v1/orders", json=_payload(patient_first_name="Alice"))
    client.post("/api/v1/orders", json=_payload(patient_first_name="Bob", status="completed"))

    r = client.get("/api/v1/orders?search=alice")
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(i["patient_first_name"] == "Alice" for i in items)

    r = client.get("/api/v1/orders?status=completed")
    items = r.json()["items"]
    assert all(i["status"] == "completed" for i in items)


def test_update_order(client):
    created = client.post("/api/v1/orders", json=_payload()).json()
    r = client.patch(
        f"/api/v1/orders/{created['id']}",
        json={"status": "completed", "notes": "All done"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["notes"] == "All done"


def test_delete_order(client):
    created = client.post("/api/v1/orders", json=_payload()).json()
    r = client.delete(f"/api/v1/orders/{created['id']}")
    assert r.status_code == 204

    r = client.get(f"/api/v1/orders/{created['id']}")
    assert r.status_code == 404


def test_404_unknown_order(client):
    r = client.get(f"/api/v1/orders/{uuid.uuid4()}")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["type"] == "http_error"


def test_validation_blank_name(client):
    r = client.post("/api/v1/orders", json=_payload(patient_first_name=""))
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["type"] == "validation_error"


def test_validation_future_dob(client):
    r = client.post("/api/v1/orders", json=_payload(patient_dob="2999-01-01"))
    assert r.status_code == 422

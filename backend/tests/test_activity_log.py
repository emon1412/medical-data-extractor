"""Activity logs are written by middleware on each request and exposed via API."""


def test_activity_log_records_request(client):
    r = client.post(
        "/api/v1/orders",
        json={"patient_first_name": "Test", "patient_last_name": "Patient"},
    )
    assert r.status_code == 201
    new_id = r.json()["id"]
    # The create endpoint should expose the new resource id via header
    assert r.headers.get("X-Resource-ID") == new_id

    r = client.get("/api/v1/activity-logs?path_contains=orders")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert any(
        item["path"] == "/api/v1/orders" and item["method"] == "POST"
        for item in body["items"]
    )


def test_activity_log_captures_semantic_fields(client):
    """Each request should be tagged with action + resource_type + resource_id."""
    r = client.post(
        "/api/v1/orders",
        json={"patient_first_name": "Sem", "patient_last_name": "Antic"},
    )
    assert r.status_code == 201
    order_id = r.json()["id"]

    client.get(f"/api/v1/orders/{order_id}")
    client.patch(f"/api/v1/orders/{order_id}", json={"status": "completed"})

    # Filter by resource_id — this is the "what happened to order X?" use case
    r = client.get(f"/api/v1/activity-logs?resource_id={order_id}")
    body = r.json()
    actions = sorted({i["action"] for i in body["items"]})
    assert "order.created" in actions
    assert "order.read" in actions
    assert "order.updated" in actions
    assert all(i["resource_type"] == "order" for i in body["items"])
    assert all(i["resource_id"] == order_id for i in body["items"])

    # Filter by action verb — the "show me every create" use case
    r = client.get("/api/v1/activity-logs?action=order.created")
    assert r.status_code == 200
    assert all(i["action"] == "order.created" for i in r.json()["items"])


def test_activity_log_pagination(client):
    for _ in range(3):
        client.get("/api/v1/orders")
    r = client.get("/api/v1/activity-logs?limit=2&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert body["limit"] == 2
    assert len(body["items"]) <= 2

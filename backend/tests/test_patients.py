"""Patient entity: find-or-create on order creation, list/get endpoints,
patient -> orders relationship."""


def _payload(first="Marie", last="Curie", dob="1900-12-05", **extra):
    return {
        "patient_first_name": first,
        "patient_last_name": last,
        "patient_dob": dob,
        **extra,
    }


def test_creating_two_orders_for_same_patient_links_one_patient(client):
    a = client.post("/api/v1/orders", json=_payload()).json()
    b = client.post("/api/v1/orders", json=_payload()).json()

    # Both orders should reference the same patient_id
    assert a["patient_id"] is not None
    assert a["patient_id"] == b["patient_id"]


def test_patient_list_includes_order_count(client):
    client.post("/api/v1/orders", json=_payload())
    client.post("/api/v1/orders", json=_payload())
    client.post("/api/v1/orders", json=_payload(first="Ada", last="Lovelace", dob=None))

    r = client.get("/api/v1/patients")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2

    by_name = {f"{p['first_name']} {p['last_name']}": p for p in body["items"]}
    assert by_name["Marie Curie"]["order_count"] == 2
    assert by_name["Ada Lovelace"]["order_count"] == 1


def test_get_patient_orders(client):
    a = client.post("/api/v1/orders", json=_payload()).json()
    b = client.post("/api/v1/orders", json=_payload()).json()
    patient_id = a["patient_id"]

    r = client.get(f"/api/v1/patients/{patient_id}/orders")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    ids = {o["id"] for o in body["items"]}
    assert ids == {a["id"], b["id"]}


def test_patient_search_case_insensitive(client):
    client.post("/api/v1/orders", json=_payload(first="MARIE", last="curie"))
    r = client.get("/api/v1/patients?search=cur")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["last_name"] == "curie"


def test_unknown_patient_returns_404(client):
    r = client.get("/api/v1/patients/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert r.json()["error"]["type"] == "http_error"

from datetime import datetime

YEAR = datetime.now().year
MINIMAL_TRIP = {"first_pickup_country": "FI"}


def _post_trip(c):
    resp = c.post("/api/trips", json=MINIMAL_TRIP)
    assert resp.status_code == 201
    return resp.get_json()


def _delete_trip(c, db_id):
    resp = c.delete(f"/api/trips/{db_id}")
    assert resp.status_code == 200


def test_trip_id_first(client):
    c, _ = client
    data = _post_trip(c)
    assert data["trip_id"] == f"TRP-{YEAR}-001"


def test_trip_id_sequential(client):
    c, _ = client
    ids = [_post_trip(c)["trip_id"] for _ in range(3)]
    assert ids == [f"TRP-{YEAR}-001", f"TRP-{YEAR}-002", f"TRP-{YEAR}-003"]


def test_trip_id_after_middle_delete(client):
    """Deleting the middle row: MAX stays at 3, next gets 004."""
    c, _ = client
    r1 = _post_trip(c)
    r2 = _post_trip(c)
    r3 = _post_trip(c)
    _delete_trip(c, r2["id"])
    r4 = _post_trip(c)
    assert r4["trip_id"] == f"TRP-{YEAR}-004"


def test_trip_id_after_last_delete(client):
    """Deleting the last row: number repeats (003) — acceptable in demo, no UNIQUE error."""
    c, _ = client
    r1 = _post_trip(c)
    r2 = _post_trip(c)
    r3 = _post_trip(c)
    _delete_trip(c, r3["id"])
    r_new = _post_trip(c)
    assert r_new["trip_id"] == f"TRP-{YEAR}-003"
    assert r_new["id"] is not None

import sqlite3


def _setup_trip_env(c, db_path):
    """Insert carrier, trailer and trip into test DB; fuel rate via the API."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "INSERT INTO carriers (name, country, city) VALUES ('Demo Carrier', 'FI', 'Helsinki')"
    )
    carrier_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.execute(
        "INSERT INTO trailers (plate_number, identifier, trailer_type, leasing_rate, rental_rate) "
        "VALUES ('TST-001', 'T-001', 'Pressutrailer', 35.0, 54.0)"
    )
    trailer_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.execute(
        "INSERT INTO trips (trip_id, status, first_pickup_country, "
        "loading_date, delivery_date, carrier_id, trailer_id, trailer_type) "
        "VALUES ('TRP-TEST-001', 'Suunniteltu', 'FI', "
        "'2026-11-03', '2026-11-07', ?, ?, 'Pressutrailer')",
        (carrier_id, trailer_id),
    )
    trip_db_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.commit()
    conn.close()
    resp = c.post("/api/fuel-rates", json={
        "valid_from": "2026-11-01", "valid_to": "2026-11-30", "multiplier": 1.18,
    })
    assert resp.status_code == 201
    return trip_db_id


def test_fuel_surcharge_added_on_freight(client):
    c, db_path = client
    trip_id = _setup_trip_env(c, db_path)

    resp = c.post(f"/api/trips/{trip_id}/costs", json={
        "cost_code": "120", "description": "FREIGHT",
        "amount": 1000.0, "cost_type": "revenue",
    })
    assert resp.status_code == 201
    assert resp.get_json().get("fuel_surcharge_added") is True

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT amount, cost_type FROM costs WHERE trip_id=? AND cost_code='200'",
        (trip_id,),
    ).fetchone()
    conn.close()
    assert row is not None
    assert round(row["amount"], 2) == 180.0   # 1000 × (1.18 − 1.0)
    assert row["cost_type"] == "revenue"


def test_no_fuel_surcharge_for_spot(client):
    c, db_path = client
    trip_id = _setup_trip_env(c, db_path)

    resp = c.post(f"/api/trips/{trip_id}/costs", json={
        "cost_code": "100", "description": "SPOT PRICE",
        "amount": 1500.0, "cost_type": "revenue",
    })
    assert resp.status_code == 201
    assert "fuel_surcharge_added" not in resp.get_json()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id FROM costs WHERE trip_id=? AND cost_code='200'", (trip_id,)
    ).fetchone()
    conn.close()
    assert row is None


def test_fuel_surcharge_type_is_revenue(client):
    """Auto-inserted code 200 must have cost_type='revenue', not 'cost'."""
    c, db_path = client
    trip_id = _setup_trip_env(c, db_path)

    c.post(f"/api/trips/{trip_id}/costs", json={
        "cost_code": "120", "description": "FREIGHT",
        "amount": 2000.0, "cost_type": "revenue",
    })

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT cost_type FROM costs WHERE trip_id=? AND cost_code='200'", (trip_id,)
    ).fetchone()
    conn.close()
    assert row["cost_type"] == "revenue"


def _trailer_rows(db_path, trip_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT cost_code, amount, cost_type FROM costs WHERE trip_id=? ORDER BY cost_type",
        (trip_id,),
    ).fetchall()
    conn.close()
    return rows


def test_trailer_rental_added_on_confirmation(client):
    """Status → Vahvistettu adds two code-400 rows: cost (leasing) + revenue (rental)."""
    c, db_path = client
    trip_id = _setup_trip_env(c, db_path)

    resp = c.put(f"/api/trips/{trip_id}/status", json={"status": "Vahvistettu"})
    assert resp.status_code == 200

    rows = _trailer_rows(db_path, trip_id)
    assert [r["cost_code"] for r in rows] == ["400", "400"]
    by_type = {r["cost_type"]: r for r in rows}
    # loading 2026-11-03, delivery 2026-11-07 → (7−3) + 1 = 5 days
    assert by_type["cost"]["amount"] == 175.0     # 5 × 35.0
    assert by_type["revenue"]["amount"] == 270.0  # 5 × 54.0


def test_trailer_rental_not_duplicated(client):
    """Re-confirming a trip must not add the trailer rows again."""
    c, db_path = client
    trip_id = _setup_trip_env(c, db_path)

    c.put(f"/api/trips/{trip_id}/status", json={"status": "Vahvistettu"})
    c.put(f"/api/trips/{trip_id}/status", json={"status": "Suunniteltu"})
    c.put(f"/api/trips/{trip_id}/status", json={"status": "Vahvistettu"})

    rows = _trailer_rows(db_path, trip_id)
    assert len(rows) == 2


def test_no_legacy_trailer_code(client):
    c, db_path = client
    trip_id = _setup_trip_env(c, db_path)
    c.put(f"/api/trips/{trip_id}/status", json={"status": "Vahvistettu"})
    codes = {r["cost_code"] for r in _trailer_rows(db_path, trip_id)}
    assert "401" not in codes

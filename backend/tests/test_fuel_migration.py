"""Polttoainelisän siirto lisähintatauluun (issue #4, spec luku 7.5).

fuel_rates → surcharge_rates (200 / revenue / percent), 120 → 200 -automaatti
calculate_surcharge-funktiolla ja /api/fuel-rates yhteensopivuuskerroksena.
Kaikki kertoimet ja summat ovat demodataa.
"""
import sqlite3
from decimal import Decimal

import pytest

import money

from init_db import create_schema
from surcharges import (
    FUEL_ROW_FILTER, calculate_surcharge, ensure_surcharge_rates,
    migrate_fuel_rates, multiplier_to_rate, rate_to_multiplier,
)

# init_db.seed_demo_data: fuel_rates-demoarvot
DEMO_FUEL_RATES = [
    ("2026-01-01", "2026-01-31", 1.15),
    ("2026-02-01", "2026-02-28", 1.16),
    ("2026-03-01", "2026-03-31", 1.18),
    ("2026-04-01", "2026-04-30", 1.17),
    ("2026-05-01", "2026-05-31", 1.19),
]


@pytest.fixture
def legacy_conn():
    """Muistikanta, jossa vanha fuel_rates ja tyhjä surcharge_rates."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    create_schema(c)
    ensure_surcharge_rates(c)
    c.executemany(
        "INSERT INTO fuel_rates (valid_from, valid_to, multiplier) VALUES (?, ?, ?)",
        DEMO_FUEL_RATES,
    )
    yield c
    c.close()


def fuel_rows(conn):
    return [money.row_from_db("surcharge_rates", r) for r in conn.execute(
        f"SELECT * FROM surcharge_rates WHERE {FUEL_ROW_FILTER} ORDER BY valid_from"
    ).fetchall()]


def old_fuel_amount(freight, multiplier):
    """Ennen siirtoa käytetty kaava (app.add_cost), Decimalina vertailua varten."""
    return Decimal(str(round(float(freight) * (multiplier - 1.0), 2)))


# ── Muunnokset ────────────────────────────────────────────────────────

@pytest.mark.parametrize("multiplier, rate", [
    (1.15, 15.0), (1.18, 18.0), (1.185, 18.5), (1.0, 0.0), (1.12345, 12.345),
])
def test_multiplier_rate_roundtrip(multiplier, rate):
    assert multiplier_to_rate(multiplier) == Decimal(str(rate))
    assert rate_to_multiplier(rate) == Decimal(str(multiplier))


def test_rate_has_no_float_noise():
    # (1.18 − 1) × 100 = 18.000000000000014 ilman pyöristystä
    assert multiplier_to_rate(1.18) == 18.0


# ── Siirto ────────────────────────────────────────────────────────────

def test_migration_copies_demo_rates(legacy_conn):
    assert migrate_fuel_rates(legacy_conn) == 5
    rows = fuel_rows(legacy_conn)
    assert [(r["valid_from"], r["valid_to"], r["rate"]) for r in rows] == [
        ("2026-01-01", "2026-01-31", 15.0),
        ("2026-02-01", "2026-02-28", 16.0),
        ("2026-03-01", "2026-03-31", 18.0),
        ("2026-04-01", "2026-04-30", 17.0),
        ("2026-05-01", "2026-05-31", 19.0),
    ]
    for r in rows:
        assert (r["service_code"], r["cost_type"], r["rate_type"]) == (
            "200", "revenue", "percent")
        assert r["min_amount"] is None and r["max_amount"] is None


def test_migration_is_repeatable(legacy_conn):
    migrate_fuel_rates(legacy_conn)
    assert migrate_fuel_rates(legacy_conn) == 0
    assert len(fuel_rows(legacy_conn)) == 5


def test_migration_runs_only_once(legacy_conn):
    """Siirron jälkeen surcharge_rates on ainoa lähde: poistettu rivi ei palaa."""
    migrate_fuel_rates(legacy_conn)
    legacy_conn.execute(
        f"DELETE FROM surcharge_rates WHERE {FUEL_ROW_FILTER} AND valid_from = '2026-01-01'"
    )
    migrate_fuel_rates(legacy_conn)
    assert len(fuel_rows(legacy_conn)) == 4


def test_migration_skips_existing_identical_row(legacy_conn):
    legacy_conn.execute(
        "INSERT INTO surcharge_rates (service_code, cost_type, rate_type, rate_e4, "
        "valid_from, valid_to) VALUES ('200', 'revenue', 'percent', 180000, "
        "'2026-03-01', '2026-03-31')"
    )
    assert migrate_fuel_rates(legacy_conn) == 4
    assert len(fuel_rows(legacy_conn)) == 5


@pytest.mark.parametrize("multiplier", [1.0, 0.95])
def test_migration_skips_multiplier_at_most_one(legacy_conn, multiplier):
    legacy_conn.execute(
        "INSERT INTO fuel_rates (valid_from, valid_to, multiplier) "
        "VALUES ('2026-06-01', '2026-06-30', ?)", (multiplier,)
    )
    assert migrate_fuel_rates(legacy_conn) == 5
    assert all(r["valid_from"] != "2026-06-01" for r in fuel_rows(legacy_conn))


def test_migration_without_fuel_table_is_noop():
    c = sqlite3.connect(":memory:")
    ensure_surcharge_rates(c)
    assert migrate_fuel_rates(c) == 0
    c.close()


def test_demo_db_is_migrated(demo_client):
    """conftest: seed_demo_data + migraatiot → demokertoimet surcharge_rates-taulussa."""
    _, db_path = demo_client
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    assert [r["rate"] for r in fuel_rows(conn)] == [15.0, 16.0, 18.0, 17.0, 19.0]
    conn.close()


# ── Summien vastaavuus ────────────────────────────────────────────────

FREIGHT_AMOUNTS = [0.01, 1, 99.99, 100, 333.33, 999.99, 1000, 1234.56,
                   1500, 2000, 2345.67, 3000, 4321.09, 9999.99, 12345.67]


@pytest.mark.parametrize("valid_from, valid_to, multiplier", DEMO_FUEL_RATES)
def test_amount_same_as_before_migration(legacy_conn, valid_from, valid_to, multiplier):
    migrate_fuel_rates(legacy_conn)
    for freight in FREIGHT_AMOUNTS:
        result = calculate_surcharge("200", {
            "cost_type": "revenue", "date": valid_from, "freight_amount": freight,
        }, legacy_conn)
        assert result["amount"] == old_fuel_amount(freight, multiplier), freight
        assert result["rate_type"] == "percent"


def test_no_fuel_surcharge_outside_validity(legacy_conn):
    migrate_fuel_rates(legacy_conn)
    assert calculate_surcharge("200", {
        "cost_type": "revenue", "date": "2026-07-15", "freight_amount": 1000,
    }, legacy_conn) is None


# ── 120 → 200 -automaatti ─────────────────────────────────────────────

def _make_trip(db_path, loading_date):
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "INSERT INTO trips (trip_id, status, loading_date) VALUES ('TRP-FUEL-1', 'Suunniteltu', ?)",
        (loading_date,),
    )
    trip_id = cur.lastrowid
    conn.commit()
    conn.close()
    return trip_id


def _fuel_costs(db_path, trip_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM costs WHERE trip_id = ? AND cost_code = '200'", (trip_id,)
    ).fetchall()
    conn.close()
    return [money.row_from_db("costs", r) for r in rows]


@pytest.mark.parametrize("loading_date, multiplier", [
    ("2026-01-15", 1.15), ("2026-03-10", 1.18), ("2026-05-31", 1.19),
])
def test_freight_uses_migrated_demo_rate(demo_client, loading_date, multiplier):
    c, db_path = demo_client
    trip_id = _make_trip(db_path, loading_date)
    resp = c.post(f"/api/trips/{trip_id}/costs", json={
        "cost_code": "120", "description": "FREIGHT",
        "amount": 2345.67, "cost_type": "revenue",
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["fuel_surcharge_added"] is True
    rows = _fuel_costs(db_path, trip_id)
    assert len(rows) == 1
    assert rows[0]["id"] == body["fuel_surcharge_id"]
    assert rows[0]["amount"] == old_fuel_amount(2345.67, multiplier)
    assert rows[0]["cost_type"] == "revenue"
    assert rows[0]["description"] == f"POLTTOAINELISÄ (kerroin {multiplier})"


def test_freight_without_valid_rate_adds_nothing(demo_client):
    c, db_path = demo_client
    trip_id = _make_trip(db_path, "2027-06-01")
    resp = c.post(f"/api/trips/{trip_id}/costs", json={
        "cost_code": "120", "description": "FREIGHT",
        "amount": 1000, "cost_type": "revenue",
    })
    assert resp.status_code == 201
    assert "fuel_surcharge_added" not in resp.get_json()
    assert _fuel_costs(db_path, trip_id) == []


def test_multiplier_one_adds_nothing(client):
    c, db_path = client
    assert c.post("/api/fuel-rates", json={
        "valid_from": "2026-11-01", "valid_to": "2026-11-30", "multiplier": 1.0,
    }).status_code == 201
    trip_id = _make_trip(db_path, "2026-11-10")
    resp = c.post(f"/api/trips/{trip_id}/costs", json={
        "cost_code": "120", "description": "FREIGHT",
        "amount": 1000, "cost_type": "revenue",
    })
    assert "fuel_surcharge_added" not in resp.get_json()
    assert _fuel_costs(db_path, trip_id) == []


def test_fuel_rates_table_no_longer_read(client):
    """Suoraan vanhaan tauluun lisätty kerroin ei vaikuta laskentaan."""
    c, db_path = client
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO fuel_rates (valid_from, valid_to, multiplier) "
        "VALUES ('2026-11-01', '2026-11-30', 1.18)"
    )
    conn.commit()
    conn.close()
    trip_id = _make_trip(db_path, "2026-11-10")
    resp = c.post(f"/api/trips/{trip_id}/costs", json={
        "cost_code": "120", "description": "FREIGHT",
        "amount": 1000, "cost_type": "revenue",
    })
    assert "fuel_surcharge_added" not in resp.get_json()
    assert c.get("/api/fuel-rates").get_json() == []


# ── /api/fuel-rates -yhteensopivuus ───────────────────────────────────

LEGACY_KEYS = {"id", "valid_from", "valid_to", "multiplier", "created_at"}


def test_api_get_lists_demo_rates_newest_first(demo_client):
    c, _ = demo_client
    rates = c.get("/api/fuel-rates").get_json()
    assert [r["multiplier"] for r in rates] == [1.19, 1.17, 1.18, 1.16, 1.15]
    assert all(set(r) == LEGACY_KEYS for r in rates)
    assert rates[0]["valid_from"] == "2026-05-01"
    assert rates[0]["valid_to"] == "2026-05-31"


def test_api_current(demo_client):
    c, _ = demo_client
    resp = c.get("/api/fuel-rates/current?date=2026-03-15")
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body) == LEGACY_KEYS
    assert body["multiplier"] == 1.18
    assert body["valid_from"] == "2026-03-01"


def test_api_current_not_found(demo_client):
    c, _ = demo_client
    resp = c.get("/api/fuel-rates/current?date=2027-01-01")
    assert resp.status_code == 404
    assert resp.get_json()["multiplier"] is None


def test_api_post_writes_surcharge_row(client):
    c, db_path = client
    resp = c.post("/api/fuel-rates", json={
        "valid_from": "2026-11-01", "valid_to": "2026-11-30", "multiplier": 1.185,
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["message"] == "Kerroin lisätty"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM surcharge_rates WHERE id = ?", (body["id"],)).fetchone()
    assert (row["service_code"], row["cost_type"], row["rate_type"], row["rate_e4"]) == (
        "200", "revenue", "percent", 185000)
    assert conn.execute("SELECT COUNT(*) FROM fuel_rates").fetchone()[0] == 0
    conn.close()
    assert c.get("/api/fuel-rates").get_json()[0]["multiplier"] == 1.185


@pytest.mark.parametrize("payload", [
    {"valid_to": "2026-11-30", "multiplier": 1.18},
    {"valid_from": "2026-11-01", "multiplier": 1.18},
    {"valid_from": "2026-11-01", "valid_to": "2026-11-30"},
    {"valid_from": "2026-11-01", "valid_to": "2026-11-30", "multiplier": "abc"},
    {"valid_from": "2026-11-01", "valid_to": "2026-11-30", "multiplier": 0.9},
    {"valid_from": "2026-11-30", "valid_to": "2026-11-01", "multiplier": 1.18},
])
def test_api_post_invalid(client, payload):
    c, _ = client
    resp = c.post("/api/fuel-rates", json=payload)
    assert resp.status_code == 400
    assert resp.get_json()["error"]


def test_api_post_overlap_conflict(demo_client):
    c, _ = demo_client
    resp = c.post("/api/fuel-rates", json={
        "valid_from": "2026-05-15", "valid_to": "2026-06-15", "multiplier": 1.2,
    })
    assert resp.status_code == 409


def test_api_put_updates_rate(demo_client):
    c, _ = demo_client
    rate = c.get("/api/fuel-rates/current?date=2026-03-15").get_json()
    resp = c.put(f"/api/fuel-rates/{rate['id']}", json={
        "valid_from": "2026-03-01", "valid_to": "2026-03-31", "multiplier": 1.2,
    })
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Kerroin päivitetty"
    assert c.get("/api/fuel-rates/current?date=2026-03-15").get_json()["multiplier"] == 1.2


def test_api_put_delete_reject_non_fuel_rows(demo_client):
    """Muiden lisien rivejä ei voi muokata eikä poistaa /api/fuel-rates-kautta."""
    c, db_path = demo_client
    conn = sqlite3.connect(db_path)
    other_id = conn.execute(
        "SELECT id FROM surcharge_rates WHERE service_code = '530' LIMIT 1"
    ).fetchone()[0]
    conn.close()
    assert c.put(f"/api/fuel-rates/{other_id}", json={
        "valid_from": "2026-01-01", "valid_to": "2026-01-31", "multiplier": 1.1,
    }).status_code == 404
    assert c.delete(f"/api/fuel-rates/{other_id}").status_code == 404
    assert c.delete("/api/fuel-rates/99999").status_code == 404


def test_api_delete_removes_rate_and_surcharge(client):
    c, db_path = client
    rate_id = c.post("/api/fuel-rates", json={
        "valid_from": "2026-11-01", "valid_to": "2026-11-30", "multiplier": 1.18,
    }).get_json()["id"]
    resp = c.delete(f"/api/fuel-rates/{rate_id}")
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "Kerroin poistettu"
    assert c.get("/api/fuel-rates").get_json() == []

    trip_id = _make_trip(db_path, "2026-11-10")
    resp = c.post(f"/api/trips/{trip_id}/costs", json={
        "cost_code": "120", "description": "FREIGHT",
        "amount": 1000, "cost_type": "revenue",
    })
    assert "fuel_surcharge_added" not in resp.get_json()

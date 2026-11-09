"""Rahasummat (issue #22): Decimal-laskenta, pyöristys ja kanta/API-muunnokset."""
import os
import re
import sqlite3
from decimal import Decimal

import pytest

import money

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Pyöristys ─────────────────────────────────────────────────────────

def test_point_one_plus_point_two():
    # float: 0.1 + 0.2 = 0.30000000000000004
    assert money.total(["0.1", "0.2"]) == Decimal("0.3")
    assert money.to_cents(money.total([0.1, 0.2])) == 30
    assert money.to_cents(0.1 + 0.2) == 30


@pytest.mark.parametrize("value, expected", [
    ("0.125", "0.13"), ("2.675", "2.68"), ("1.005", "1.01"), ("2.665", "2.67"),
    ("0.124", "0.12"), ("-0.125", "-0.13"), ("100", "100.00"),
    (2.675, "2.68"),   # float-syöte luetaan lyhimmästä esityksestä, ei 2.67499…
    (1.005, "1.01"),
])
def test_round_money_half_up(value, expected):
    assert money.round_money(value) == Decimal(expected)
    assert str(money.round_money(value)) == expected


def test_sum_of_many_cents_is_exact():
    # 1000 × 0,10 € floatilla = 99.9999999999986
    assert money.total(["0.10"] * 1000) == Decimal("100.00")
    assert sum(money.to_cents("0.10") for _ in range(1000)) == 10000


@pytest.mark.parametrize("value, cents", [
    ("180", 18000), ("180.00", 18000), ("12,50", 1250), (" 1 234,56 ", 123456),
    (0, 0), (Decimal("0.005"), 1), ("-3.50", -350), (None, None), ("", None),
])
def test_to_cents(value, cents):
    assert money.to_cents(value) == cents


def test_from_cents_roundtrip():
    for cents in (0, 1, 30, 18000, 123456, -350):
        assert money.to_cents(money.from_cents(cents)) == cents
    assert money.from_cents(18000) == Decimal("180.00")
    assert money.from_cents(None) is None


def test_e4_scale_for_unit_prices_and_percentages():
    assert money.to_e4("12.345") == 123450
    assert money.to_e4("1.85") == 18500
    assert money.to_e4("0.00005") == 1      # ROUND_HALF_UP neljään desimaaliin
    assert money.from_e4(123450) == Decimal("12.3450")


def test_from_minor_rejects_float_from_db():
    with pytest.raises(ValueError):
        money.from_cents(180.0)


@pytest.mark.parametrize("bad", ["abc", "1.2.3", "NaN", "inf", "-Infinity", True, [1], {}])
def test_to_decimal_rejects_invalid(bad):
    with pytest.raises(ValueError):
        money.to_decimal(bad)


def test_percent_of():
    assert money.percent_of("942.00", "5387.00") == Decimal("17.49")
    assert money.percent_of("942.00", "5387.00", places=1) == Decimal("17.5")
    assert money.percent_of("10", "0") == Decimal("0")


def test_row_conversion_roundtrip():
    db = {"id": 1, "amount_cents": 27550, "cost_type": "cost"}
    api = money.row_from_db("costs", db)
    assert api == {"id": 1, "amount": Decimal("275.50"), "cost_type": "cost"}
    assert money.values_to_db("costs", api) == db
    assert money.column("surcharge_rates", "rate") == "rate_e4"
    assert money.column("surcharge_rates", "service_code") == "service_code"


def test_no_float_in_money_code():
    """Rahalaskentamoduuleissa ei muunneta floatiksi."""
    for name in ("money.py", "surcharges.py", "customer_pricing.py"):
        with open(os.path.join(BACKEND_DIR, name), encoding="utf-8") as f:
            source = f.read()
        assert not re.search(r"\bfloat\(", source), name
        assert not re.search(r"\bround\(", source), name


# ── API: kanta sentteinä, JSON euroina ────────────────────────────────

def _trip(db_path):
    conn = sqlite3.connect(db_path)
    trip_id = conn.execute(
        "INSERT INTO trips (trip_id, status) VALUES ('TRP-MONEY-1', 'Suunniteltu')"
    ).lastrowid
    conn.commit()
    conn.close()
    return trip_id


def _post_cost(c, trip_id, amount, code="799", cost_type="cost"):
    return c.post(f"/api/trips/{trip_id}/costs", json={
        "cost_code": code, "description": "TESTI", "amount": amount, "cost_type": cost_type,
    })


def test_api_cost_sum_is_exact(client):
    c, db_path = client
    trip_id = _trip(db_path)
    for amount in ("0.10", "0.20", 0.1, 0.2):
        assert _post_cost(c, trip_id, amount).status_code == 201
    trip = c.get(f"/api/trips/{trip_id}").get_json()
    assert trip["total_costs"] == 0.6
    assert [r["amount"] for r in trip["costs"]] == [0.1, 0.2, 0.1, 0.2]

    conn = sqlite3.connect(db_path)
    stored = conn.execute(
        "SELECT amount_cents, typeof(amount_cents) FROM costs WHERE trip_id = ? ORDER BY id",
        (trip_id,)).fetchall()
    conn.close()
    assert stored == [(10, "integer"), (20, "integer"), (10, "integer"), (20, "integer")]


def test_api_accepts_string_with_comma_and_rounds_half_up(client):
    c, db_path = client
    trip_id = _trip(db_path)
    assert _post_cost(c, trip_id, "12,345").status_code == 201
    costs = c.get(f"/api/trips/{trip_id}/costs").get_json()
    assert costs[0]["amount"] == 12.35


@pytest.mark.parametrize("bad", ["abc", "NaN", True])
def test_api_rejects_invalid_amount(client, bad):
    c, db_path = client
    trip_id = _trip(db_path)
    resp = _post_cost(c, trip_id, bad)
    assert resp.status_code == 400
    assert "amount ei ole numero" in resp.get_json()["error"]


def test_api_dashboard_margin_is_exact(client):
    c, db_path = client
    trip_id = _trip(db_path)
    _post_cost(c, trip_id, "0.30", code="100", cost_type="revenue")
    _post_cost(c, trip_id, "0.10")
    _post_cost(c, trip_id, "0.20")
    t = next(t for t in c.get("/api/dashboard").get_json()["trips"] if t["id"] == trip_id)
    assert (t["total_revenue"], t["total_costs"], t["margin"]) == (0.3, 0.3, 0.0)
    cd = c.get("/api/costs-dashboard").get_json()
    row = next(r for r in cd["trips"] if r["id"] == trip_id)
    assert row["margin"] == 0.0


def test_api_rate_endpoints_keep_euro_format(client):
    c, _ = client
    km = c.post("/api/km-rates", json={
        "valid_from": "2030-01-01", "domestic_rate": "1.875", "continent_rate": 2.2})
    assert km.status_code == 201
    assert (km.get_json()["domestic_rate"], km.get_json()["continent_rate"]) == (1.875, 2.2)
    assert "domestic_rate_e4" not in km.get_json()

    ferry = c.post("/api/ferry-rates-db", json={
        "route": "Demo A - Demo B", "price": "999.99", "valid_from": "2030-01-01"})
    assert ferry.status_code == 201
    assert ferry.get_json()["price"] == 999.99

    assert c.post("/api/km-rates", json={"valid_from": "2030-01-01"}).status_code == 400
    assert c.post("/api/ferry-rates-db", json={"route": "X", "price": "x"}).status_code == 400


def test_api_trailer_rates_in_cents(client):
    c, db_path = client
    resp = c.post("/api/trailers", json={
        "plate_number": "MNY-001", "trailer_type": "Pressutrailer",
        "leasing_rate": "35.5", "rental_rate": 54})
    assert resp.status_code == 201
    trailer = next(t for t in c.get("/api/trailers").get_json() if t["plate_number"] == "MNY-001")
    assert (trailer["leasing_rate"], trailer["rental_rate"]) == (35.5, 54.0)
    conn = sqlite3.connect(db_path)
    assert conn.execute(
        "SELECT leasing_rate_cents, rental_rate_cents FROM trailers WHERE plate_number = 'MNY-001'"
    ).fetchone() == (3550, 5400)
    conn.close()
    assert c.post("/api/trailers", json={
        "plate_number": "MNY-002", "trailer_type": "Pressutrailer", "leasing_rate": "abc",
    }).status_code == 400

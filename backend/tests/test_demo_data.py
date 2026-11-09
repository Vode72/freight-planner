"""Demodatan testit (issue #14).

Oikeita yritysnimiä ei listata tässä kieltolistana, koska ne päätyisivät
silloin takaisin repoon. Sen sijaan testit varmistavat positiivisesti, että
jokainen demodatan yritysnimi sisältää sanan "Demo".
"""
import sqlite3

import pytest

import app as flask_app
from reset_demo import reset_demo

MIN_MARGIN_PCT = 8.0
MAX_MARGIN_PCT = 20.0
SPOT_CODE = "100"
TRAILER_RENT_CODE = "400"


@pytest.fixture
def demo_db(tmp_path):
    db_path = str(tmp_path / "demo.db")
    reset_demo(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def _assert_demo_names(rows, label):
    assert rows, f"{label}: ei rivejä"
    bad = [r for r in rows if not r or "Demo" not in r]
    assert not bad, f"{label}: nimet ilman 'Demo'-sanaa: {bad}"


# ── Yritysnimet ───────────────────────────────────────────────────────

def test_customer_names_are_demo(demo_db):
    names = [r[0] for r in demo_db.execute("SELECT name FROM customers")]
    _assert_demo_names(names, "customers")


def test_carrier_names_are_demo(demo_db):
    names = [r[0] for r in demo_db.execute("SELECT name FROM carriers")]
    _assert_demo_names(names, "carriers")


@pytest.mark.parametrize("column", [
    "consignor_name", "consignee_name", "loading_point_name", "unloading_point_name",
])
def test_order_party_names_are_demo(demo_db, column):
    names = [r[0] for r in demo_db.execute(f"SELECT {column} FROM orders")]
    _assert_demo_names(names, f"orders.{column}")


def test_terminal_names_are_demo(demo_db):
    names = [r[0] for r in demo_db.execute("SELECT name FROM terminals")]
    _assert_demo_names(names, "terminals")


def test_trailer_leasing_companies_are_demo(demo_db):
    names = [r[0] for r in demo_db.execute("SELECT leasing_company FROM trailers")]
    _assert_demo_names(names, "trailers.leasing_company")


def test_forwarder_name_is_demo(demo_db):
    row = demo_db.execute(
        "SELECT value FROM settings WHERE key = 'forwarder_name'"
    ).fetchone()
    assert row and "Demo" in row[0]


def test_customer_emails_use_example_domain(demo_db):
    emails = [r[0] for r in demo_db.execute(
        "SELECT email FROM customers WHERE email IS NOT NULL AND email != ''"
    )]
    assert emails
    bad = [e for e in emails if not e.split("@")[-1].endswith("example.com")]
    assert not bad, f"Sähköpostit ilman example.com-domainia: {bad}"


def test_order_references_do_not_reuse_old_prefixes(demo_db):
    refs = [r[0] for r in demo_db.execute("SELECT order_reference FROM orders")]
    assert all(ref.startswith("D") or ref.startswith("BDF") for ref in refs), refs


def test_ferry_route_operators_are_demo():
    _assert_demo_names([r["carrier"] for r in flask_app.FERRY_ROUTES], "FERRY_ROUTES")


def test_ferry_routes_endpoint_operators_are_demo(client):
    c, _ = client
    resp = c.get("/api/ferry-routes")
    assert resp.status_code == 200
    _assert_demo_names([r["carrier"] for r in resp.get_json()], "/api/ferry-routes")


def test_new_trailer_defaults_to_demo_leasing_company(client):
    c, db_path = client
    resp = c.post("/api/trailers", json={
        "plate_number": "TST-001", "identifier": "TS-0001", "trailer_type": "Umpikaappi",
    })
    assert resp.status_code in (200, 201), resp.get_json()
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT leasing_company FROM trailers WHERE plate_number = 'TST-001'"
    ).fetchone()
    conn.close()
    assert row and "Demo" in row[0]


def test_schema_default_leasing_company_is_demo(demo_db):
    demo_db.execute(
        "INSERT INTO trailers (plate_number, identifier, trailer_type) "
        "VALUES ('TST-002', 'TS-0002', 'Umpikaappi')"
    )
    row = demo_db.execute(
        "SELECT leasing_company FROM trailers WHERE plate_number = 'TST-002'"
    ).fetchone()
    assert "Demo" in row[0]


# ── Katteet ja rivit ──────────────────────────────────────────────────

def _trip_lines(conn):
    trips = {}
    for r in conn.execute(
        "SELECT t.trip_id, c.cost_code, c.cost_type, c.amount_cents AS amount "
        "FROM costs c JOIN trips t ON t.id = c.trip_id"
    ):
        trips.setdefault(r["trip_id"], []).append(r)
    return trips


def test_every_trip_has_cost_lines(demo_db):
    trip_ids = {r[0] for r in demo_db.execute("SELECT trip_id FROM trips")}
    assert trip_ids == set(_trip_lines(demo_db))


def test_trip_margins_between_8_and_20_percent(demo_db):
    for trip_id, lines in _trip_lines(demo_db).items():
        revenue = sum(l["amount"] for l in lines if l["cost_type"] == "revenue")
        cost = sum(l["amount"] for l in lines if l["cost_type"] == "cost")
        assert revenue > 0, trip_id
        margin = (revenue - cost) / revenue * 100
        assert MIN_MARGIN_PCT <= margin <= MAX_MARGIN_PCT, (trip_id, round(margin, 2))


def test_costs_dashboard_margins_between_8_and_20_percent(tmp_path):
    db_path = str(tmp_path / "demo.db")
    reset_demo(db_path)
    original = flask_app.DB_NAME
    flask_app.DB_NAME = db_path
    try:
        with flask_app.app.test_client() as c:
            resp = c.get("/api/costs-dashboard")
    finally:
        flask_app.DB_NAME = original
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["trips"]) == 7
    for trip in data["trips"]:
        assert MIN_MARGIN_PCT <= trip["margin_pct"] <= MAX_MARGIN_PCT, trip
    assert MIN_MARGIN_PCT <= data["kpi"]["margin_pct"] <= MAX_MARGIN_PCT
    _assert_demo_names([t["carrier_name"] for t in data["trips"]], "dashboard carrier_name")


def test_spot_trips_only_have_spot_revenue(demo_db):
    spot_trips = [
        trip_id for trip_id, lines in _trip_lines(demo_db).items()
        if any(l["cost_code"] == SPOT_CODE for l in lines)
    ]
    assert spot_trips, "demodatassa pitää olla vähintään yksi spot-keikka"
    for trip_id in spot_trips:
        revenue_codes = {
            l["cost_code"] for l in _trip_lines(demo_db)[trip_id]
            if l["cost_type"] == "revenue"
        }
        assert revenue_codes == {SPOT_CODE}, (trip_id, revenue_codes)


def test_trailer_rent_has_cost_and_revenue_on_contract_trips(demo_db):
    checked = 0
    for trip_id, lines in _trip_lines(demo_db).items():
        if any(l["cost_code"] == SPOT_CODE for l in lines):
            continue
        rent_types = {l["cost_type"] for l in lines if l["cost_code"] == TRAILER_RENT_CODE}
        if rent_types:
            assert rent_types == {"cost", "revenue"}, (trip_id, rent_types)
            checked += 1
    assert checked > 0


def test_confirmed_or_later_trips_have_trailer_rent(demo_db):
    rows = demo_db.execute(
        "SELECT t.trip_id, COUNT(c.id) FROM trips t "
        "LEFT JOIN costs c ON c.trip_id = t.id AND c.cost_code = '400' "
        "WHERE t.status != 'Suunniteltu' GROUP BY t.trip_id"
    ).fetchall()
    assert rows
    assert all(count >= 1 for _, count in rows), rows

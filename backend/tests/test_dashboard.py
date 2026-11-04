"""Dashboardin summat (issue #20).

/api/dashboard liitti aiemmin orders- ja costs-taulut samaan trips-riviin,
jolloin jokainen kulurivi summautui kerran jokaista orderia kohti.
Testit käyttävät puhdasta demokantaa (reset_demo → tmp_path).
"""
import sqlite3

import pytest

import app as flask_app
from reset_demo import reset_demo


@pytest.fixture
def demo(tmp_path):
    db_path = str(tmp_path / "demo.db")
    reset_demo(db_path)
    flask_app.DB_NAME = db_path
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    with flask_app.app.test_client() as c:
        yield c, conn
    conn.close()


def _dashboard(client):
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    return resp.get_json()


def _trip(data, trip_id):
    matches = [t for t in data["trips"] if t["trip_id"] == trip_id]
    assert matches, f"{trip_id} puuttuu dashboardilta"
    return matches[0]


def _order_count(conn, trip_id):
    return conn.execute(
        "SELECT COUNT(*) FROM orders o JOIN trips t ON o.trip_id = t.id "
        "WHERE t.trip_id = ?", (trip_id,)
    ).fetchone()[0]


# ── Keikkakohtaiset summat ────────────────────────────────────────────

def test_trip_with_two_orders_not_multiplied(demo):
    client, conn = demo
    assert _order_count(conn, "TRP-2026-001") == 2
    t = _trip(_dashboard(client), "TRP-2026-001")
    assert t["total_revenue"] == 4046.0
    assert t["total_costs"] == 3300.0
    assert t["margin"] == 746.0
    assert t["margin_percent"] == 18.44
    assert t["order_count"] == 2


def test_trip_with_three_or_more_orders_not_multiplied(demo):
    client, conn = demo
    n = _order_count(conn, "TRP-2026-003")
    assert n >= 3
    t = _trip(_dashboard(client), "TRP-2026-003")
    assert t["total_revenue"] == 5387.0
    assert t["total_costs"] == 4445.0
    assert t["margin"] == 942.0
    assert t["order_count"] == n


def test_every_trip_matches_costs_table(demo):
    client, conn = demo
    data = _dashboard(client)
    assert data["trips"]
    for t in data["trips"]:
        row = conn.execute("""
            SELECT
              COALESCE(SUM(CASE WHEN cost_type='revenue' THEN amount END), 0),
              COALESCE(SUM(CASE WHEN cost_type='cost' THEN amount END), 0)
            FROM costs WHERE trip_id = ?
        """, (t["id"],)).fetchone()
        assert t["total_revenue"] == round(row[0], 2), t["trip_id"]
        assert t["total_costs"] == round(row[1], 2), t["trip_id"]
        assert t["margin"] == round(row[0] - row[1], 2), t["trip_id"]
        assert t["order_count"] == conn.execute(
            "SELECT COUNT(*) FROM orders WHERE trip_id = ?", (t["id"],)
        ).fetchone()[0], t["trip_id"]


def test_trip_without_orders_or_costs_is_zero(demo):
    client, conn = demo
    conn.execute(
        "INSERT INTO trips (trip_id, status) VALUES ('TRP-TEST-EMPTY', 'Suunniteltu')"
    )
    conn.commit()
    t = _trip(_dashboard(client), "TRP-TEST-EMPTY")
    assert t["order_count"] == 0
    assert t["total_revenue"] == 0
    assert t["total_costs"] == 0
    assert t["margin"] == 0
    assert t["margin_percent"] == 0


# ── KPI-kortit ────────────────────────────────────────────────────────

def test_kpi_matches_costs_table(demo):
    client, conn = demo
    kpi = _dashboard(client)["kpi"]
    assert kpi["total_revenue"] == 25768.5
    assert kpi["total_costs"] == 21751.0
    assert kpi["margin"] == 4017.5

    row = conn.execute("""
        SELECT
          SUM(CASE WHEN co.cost_type='revenue' THEN co.amount ELSE 0 END),
          SUM(CASE WHEN co.cost_type='cost' THEN co.amount ELSE 0 END)
        FROM costs co JOIN trips t ON co.trip_id = t.id
    """).fetchone()
    assert kpi["total_revenue"] == round(row[0], 2)
    assert kpi["total_costs"] == round(row[1], 2)


def test_kpi_matches_costs_dashboard(demo):
    client, _ = demo
    kpi = _dashboard(client)["kpi"]
    resp = client.get("/api/costs-dashboard")
    assert resp.status_code == 200
    cd = resp.get_json()["kpi"]
    assert kpi["total_revenue"] == cd["revenue"]
    assert kpi["total_costs"] == cd["costs"]
    assert kpi["margin"] == cd["margin"]


def test_kpi_counts_unchanged(demo):
    client, conn = demo
    kpi = _dashboard(client)["kpi"]
    assert kpi["total_trips"] == conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
    assert kpi["total_orders"] == conn.execute(
        "SELECT COUNT(*) FROM orders WHERE trip_id IN (SELECT id FROM trips)"
    ).fetchone()[0]

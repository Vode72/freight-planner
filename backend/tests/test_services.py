import sqlite3

import app as flask_app
from init_db import create_schema
from migrate_services import run_migration as run_services
from services import SERVICES

SPEC_CODES = {
    "100", "120", "200", "210", "211", "212", "220", "221", "222", "230",
    "300", "310", "320", "330", "340", "350",
    "400", "410", "830",
    "500", "510", "520", "530", "540",
    "600", "610", "700", "720", "799", "800", "810", "820",
}
NEW_CODES = {"211", "212", "221", "222", "230", "320", "330", "340", "350",
             "520", "530", "540", "720"}
REVENUE_CODES = {"100", "120", "200", "230", "720"}


def _services(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = {r["code"]: dict(r) for r in conn.execute("SELECT * FROM services")}
    conn.close()
    return rows


# ── Koodisto ──────────────────────────────────────────────────────────

def test_services_table_contains_spec_codes(client):
    _, db_path = client
    rows = _services(db_path)
    assert set(rows) == SPEC_CODES
    assert NEW_CODES <= set(rows)


def test_legacy_codes_not_in_services(client):
    _, db_path = client
    rows = _services(db_path)
    assert "401" not in rows
    assert "831" not in rows


def test_default_cost_types(client):
    _, db_path = client
    for code, row in _services(db_path).items():
        expected = "revenue" if code in REVENUE_CODES else "cost"
        assert row["default_cost_type"] == expected, code


def test_services_have_valid_category_and_active(client):
    _, db_path = client
    categories = {"rahti", "tiemaksut", "kalusto", "lautta", "lisat"}
    for row in _services(db_path).values():
        assert row["category"] in categories
        assert row["active"] == 1
        assert row["name"]


def test_create_schema_creates_services(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "s.db"))
    create_schema(conn)
    count = conn.execute("SELECT COUNT(*) FROM services").fetchone()[0]
    conn.close()
    assert count == len(SERVICES)


# ── API ───────────────────────────────────────────────────────────────

def test_get_services(client):
    c, _ = client
    resp = c.get("/api/services")
    assert resp.status_code == 200
    data = resp.get_json()
    assert {s["code"] for s in data} == SPEC_CODES
    first = data[0]
    assert set(first) == {"code", "name", "category", "default_cost_type", "active"}
    assert [s["code"] for s in data] == sorted(s["code"] for s in data)


def test_inactive_service_hidden_unless_all(client):
    c, db_path = client
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE services SET active = 0 WHERE code = '540'")
    conn.commit()
    conn.close()

    codes = {s["code"] for s in c.get("/api/services").get_json()}
    assert "540" not in codes
    all_codes = {s["code"] for s in c.get("/api/services?all=1").get_json()}
    assert "540" in all_codes


def test_cost_codes_uses_services_data(client):
    c, _ = client
    services = c.get("/api/services").get_json()
    cost_codes = c.get("/api/cost-codes").get_json()
    assert [cc["code"] for cc in cost_codes] == [s["code"] for s in services]
    for cc, s in zip(cost_codes, services):
        assert cc["description"] == s["name"]
        assert cc["type"] == s["default_cost_type"]


def test_costs_dashboard_categories(demo_client):
    c, _ = demo_client
    resp = c.get("/api/costs-dashboard")
    assert resp.status_code == 200
    cats = resp.get_json()["categories"]
    assert set(cats) == {"lautta", "rahti", "tiemaksut", "kalusto", "lisat"}


# ── Migraatio ─────────────────────────────────────────────────────────

def _insert_legacy_rows(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO trips (trip_id, status) VALUES ('TRP-LEG-001', 'Suunniteltu')"
    )
    trip_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.executemany(
        "INSERT INTO costs (trip_id, cost_code, description, amount, cost_type) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (trip_id, "400", "TRAILERVUOKRA (osto)", 100.0, "cost"),
            (trip_id, "401", "TRAILERVUOKRA (myynti)", 150.0, "revenue"),
            (trip_id, "830", "YLIKÄYTTÖ (osto)", 20.0, "cost"),
            (trip_id, "831", "YLIKÄYTTÖ (myynti)", 35.0, "revenue"),
            (trip_id, "120", "FREIGHT", 1000.0, "revenue"),
        ],
    )
    conn.commit()
    conn.close()
    return trip_id


def _cost_rows(db_path, trip_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT cost_code, description, amount, cost_type FROM costs "
        "WHERE trip_id=? ORDER BY id",
        (trip_id,),
    ).fetchall()
    conn.close()
    return [tuple(r) for r in rows]


def test_migration_merges_legacy_codes(client):
    _, db_path = client
    trip_id = _insert_legacy_rows(db_path)

    run_services(db_path)

    assert _cost_rows(db_path, trip_id) == [
        ("400", "TRAILERVUOKRA (osto)", 100.0, "cost"),
        ("400", "TRAILERVUOKRA (myynti)", 150.0, "revenue"),
        ("830", "YLIKÄYTTÖ (osto)", 20.0, "cost"),
        ("830", "YLIKÄYTTÖ (myynti)", 35.0, "revenue"),
        ("120", "FREIGHT", 1000.0, "revenue"),
    ]


def test_migration_is_idempotent(client):
    _, db_path = client
    trip_id = _insert_legacy_rows(db_path)

    run_services(db_path)
    first = _cost_rows(db_path, trip_id)
    services_first = _services(db_path)
    run_services(db_path)

    assert _cost_rows(db_path, trip_id) == first
    assert _services(db_path) == services_first


def test_migration_preserves_active_flag(client):
    _, db_path = client
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE services SET active = 0 WHERE code = '340'")
    conn.commit()
    conn.close()

    run_services(db_path)
    assert _services(db_path)["340"]["active"] == 0


def test_migration_on_db_without_services_table(tmp_path):
    """Vanha kanta: costs-taulu on, services-taulua ei."""
    db_path = str(tmp_path / "old.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE costs (id INTEGER PRIMARY KEY, trip_id INTEGER, "
        "cost_code TEXT, description TEXT, amount REAL, cost_type TEXT)"
    )
    conn.execute(
        "INSERT INTO costs (trip_id, cost_code, description, amount, cost_type) "
        "VALUES (1, '401', 'X', 10.0, 'revenue')"
    )
    conn.commit()
    conn.close()

    run_services(db_path)

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT cost_code, cost_type FROM costs").fetchone()
    n = conn.execute("SELECT COUNT(*) FROM services").fetchone()[0]
    conn.close()
    assert row == ("400", "revenue")
    assert n == len(SERVICES)


def test_migrate_db_runs_services_migration(tmp_path):
    """app.migrate_db() ajaa koodiston migraation automaattisesti."""
    db_path = str(tmp_path / "auto.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE trips (id INTEGER PRIMARY KEY, trip_id TEXT)")
    conn.execute(
        "CREATE TABLE costs (id INTEGER PRIMARY KEY, trip_id INTEGER, "
        "cost_code TEXT, description TEXT, amount REAL, cost_type TEXT)"
    )
    conn.execute(
        "INSERT INTO costs (trip_id, cost_code, description, amount, cost_type) "
        "VALUES (1, '831', 'Y', 5.0, 'revenue')"
    )
    conn.commit()
    conn.close()

    original = flask_app.DB_NAME
    flask_app.DB_NAME = db_path
    try:
        flask_app.migrate_db()
    finally:
        flask_app.DB_NAME = original

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT cost_code, cost_type FROM costs").fetchone()
    has_services = conn.execute(
        "SELECT COUNT(*) FROM services WHERE code='830'"
    ).fetchone()[0]
    conn.close()
    assert row == ("830", "revenue")
    assert has_services == 1

"""Alembic-migraatiot (issue #22): tyhjä kanta, olemassa oleva kanta, CLI."""
import os
import sqlite3
import subprocess
import sys

import pytest
import sqlalchemy.exc
from alembic.script import ScriptDirectory

import db_config
from db_migrate import (
    alembic_config, current_revision, upgrade_connection, upgrade_db,
)
from init_db import seed_demo_data

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD = ScriptDirectory.from_config(alembic_config()).get_current_head()

EXPECTED_TABLES = {
    "trips", "orders", "costs", "trailers", "carriers", "tractors", "customers",
    "fuel_rates", "services", "country_restrictions", "terminals",
    "trailer_maintenance", "km_rates", "ferry_rates", "settings",
    "surcharge_rates", "schema_migrations", "customer_rate_cards",
    "customer_billing_rules", "alembic_version",
}


def _tables(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}


def _schema(conn):
    return {t: [tuple(c[1:]) for c in conn.execute(f"PRAGMA table_info({t})")]
            for t in sorted(_tables(conn) - {"alembic_version"})}


def _data(conn):
    """Kaikkien taulujen data (paitsi alembic_version) vertailua varten."""
    return {t: sorted(map(tuple, conn.execute(f"SELECT * FROM {t}")), key=repr)
            for t in sorted(_tables(conn) - {"alembic_version"})}


# Vanhan (REAL) skeeman rivejä: hankalia liukulukuja tarkoituksella
LEGACY_ROWS = {
    "trips": [("INSERT INTO trips (id, trip_id, status) VALUES (1, 'TRP-OLD-1', 'Toimitettu')", ())],
    "trailers": [(
        "INSERT INTO trailers (id, plate_number, identifier, trailer_type, leasing_rate, rental_rate) "
        "VALUES (3, 'OLD-001', 'O-1', 'Pressutrailer', ?, ?)", (35.5, 54.0))],
    "costs": [
        ("INSERT INTO costs (id, trip_id, cost_code, description, amount, cost_type) "
         "VALUES (?, 1, '120', 'FREIGHT', ?, 'revenue')", (5, 0.1 + 0.2)),
        ("INSERT INTO costs (id, trip_id, cost_code, description, amount, cost_type) "
         "VALUES (?, 1, '200', 'POLTTOAINELISÄ', ?, 'revenue')", (6, 2.675)),
        ("INSERT INTO costs (id, trip_id, cost_code, description, amount, cost_type) "
         "VALUES (?, 1, '500', 'LAUTTA', ?, 'cost')", (9, 1.005)),
        ("INSERT INTO costs (id, trip_id, cost_code, description, amount, cost_type) "
         "VALUES (?, 1, '799', 'MUU', ?, 'cost')", (10, 275.5)),
    ],
    "km_rates": [(
        "INSERT INTO km_rates (valid_from, domestic_rate, continent_rate) VALUES ('2026-01-01', ?, ?)",
        (1.85, 2.2))],
    "ferry_rates": [(
        "INSERT INTO ferry_rates (route, price, valid_from) VALUES ('Demo A - Demo B', ?, '2026-01-01')",
        (1050,))],
    "surcharge_rates": [(
        "INSERT INTO surcharge_rates (service_code, cost_type, rate_type, rate, min_amount, "
        "max_amount, valid_from) VALUES ('520', 'cost', 'per_100kg', ?, ?, NULL, '2026-01-01')",
        (0.6, 15)), (
        "INSERT INTO surcharge_rates (service_code, cost_type, rate_type, rate, valid_from) "
        "VALUES ('200', 'revenue', 'percent', ?, '2026-01-01')", (12.345,))],
    "customers": [("INSERT INTO customers (id, name) VALUES (7, 'Vanha Demo Oy')", ())],
    "customer_rate_cards": [(
        "INSERT INTO customer_rate_cards (customer_id, origin_country, dest_country, product_type, "
        "freight_price, valid_from) VALUES (7, 'FI', 'BE', 'FTL', ?, '2026-01-01')", (1999.99,))],
    "customer_billing_rules": [
        ("INSERT INTO customer_billing_rules (customer_id, service_code, billed, rate_type, rate, "
         "valid_from) VALUES (7, '510', 1, 'pass_through', ?, '2026-01-01')", (5,)),
        ("INSERT INTO customer_billing_rules (customer_id, service_code, billed, rate_type, rate, "
         "valid_from) VALUES (7, '230', 0, NULL, NULL, '2026-01-01')", ()),
    ],
}


def _pre_alembic_db(path):
    """Kanta sellaisena kuin vanhat skriptit sen jättivät: REAL-rahasarakkeet
    ja dataa, ei alembic_version-taulua."""
    conn = sqlite3.connect(path)
    upgrade_connection(conn, "0002")
    for rows in LEGACY_ROWS.values():
        for sql, params in rows:
            conn.execute(sql, params)
    conn.execute("DELETE FROM costs WHERE id = 9")  # AUTOINCREMENT-laskuri jää 10:een
    conn.execute("DROP TABLE alembic_version")
    conn.commit()
    return conn


def test_single_head():
    assert len(ScriptDirectory.from_config(alembic_config()).get_heads()) == 1


def test_upgrade_empty_db(tmp_path):
    path = str(tmp_path / "empty.db")
    upgrade_db(path)
    conn = sqlite3.connect(path)
    assert EXPECTED_TABLES <= _tables(conn)
    assert current_revision(conn) == HEAD
    # Viitedata tulee migraatioista, demodata ei
    assert conn.execute("SELECT COUNT(*) FROM services").fetchone()[0] > 0
    assert conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 14
    for table in ("trips", "costs", "customers", "surcharge_rates", "customer_rate_cards"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    conn.close()


def test_upgrade_is_idempotent(tmp_path):
    path = str(tmp_path / "twice.db")
    upgrade_db(path)
    conn = sqlite3.connect(path)
    seed_demo_data(conn)
    conn.commit()
    before = _schema(conn), _data(conn)
    upgrade_db(path)
    assert (_schema(conn), _data(conn)) == before
    conn.close()


def test_baseline_keeps_existing_data(tmp_path):
    """Olemassa oleva (Alembicia edeltävä) kanta: baseline ei muuta dataa."""
    conn = _pre_alembic_db(str(tmp_path / "legacy.db"))
    before = _schema(conn), _data(conn)
    upgrade_connection(conn, "0002")
    assert current_revision(conn) == "0002"
    assert (_schema(conn), _data(conn)) == before
    conn.close()


def test_baseline_adds_late_columns_to_old_tables(tmp_path):
    """Vanha trips/trailers ilman ALTER-sarakkeita → baseline lisää ne."""
    path = str(tmp_path / "old.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE trips (id INTEGER PRIMARY KEY AUTOINCREMENT, trip_id TEXT)")
    conn.execute("CREATE TABLE trailers (id INTEGER PRIMARY KEY AUTOINCREMENT, plate_number TEXT)")
    conn.execute("INSERT INTO trips (trip_id) VALUES ('TRP-OLD-1')")
    conn.commit()
    upgrade_connection(conn)
    trip_cols = {r[1] for r in conn.execute("PRAGMA table_info(trips)")}
    trailer_cols = {r[1] for r in conn.execute("PRAGMA table_info(trailers)")}
    assert {"delivered_at", "tail_lift_unloading", "unloading_terminal_id"} <= trip_cols
    assert {"inspection_due", "maintenance_notes"} <= trailer_cols
    assert conn.execute("SELECT trip_id FROM trips").fetchall() == [("TRP-OLD-1",)]
    conn.close()


def test_reference_data_migration_moves_legacy_fuel_rates(tmp_path):
    """0002: vanhan kannan fuel_rates siirtyy surcharge_rates-tauluun kerran."""
    path = str(tmp_path / "fuel.db")
    conn = sqlite3.connect(path)
    upgrade_connection(conn, "0001")
    conn.executemany(
        "INSERT INTO fuel_rates (valid_from, valid_to, multiplier) VALUES (?, ?, ?)",
        [("2026-01-01", "2026-01-31", 1.15), ("2026-02-01", "2026-02-28", 1.0)],
    )
    conn.commit()
    upgrade_connection(conn)
    rows = conn.execute(
        "SELECT valid_from FROM surcharge_rates WHERE service_code = '200'"
    ).fetchall()
    assert rows == [("2026-01-01",)]  # kerroin 1.0 ohitetaan
    assert conn.execute(
        "SELECT COUNT(*) FROM schema_migrations WHERE name = 'fuel_rates_to_surcharge_rates'"
    ).fetchone()[0] == 1
    conn.close()


def test_reference_data_merges_legacy_codes(tmp_path):
    path = str(tmp_path / "codes.db")
    conn = sqlite3.connect(path)
    upgrade_connection(conn, "0001")
    conn.execute(
        "INSERT INTO costs (trip_id, cost_code, description, amount, cost_type) "
        "VALUES (1, '401', 'X', 10, 'cost')"
    )
    conn.commit()
    upgrade_connection(conn)
    assert conn.execute("SELECT cost_code FROM costs").fetchone() == ("400",)
    conn.close()


def test_upgrade_restores_connection_settings():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    upgrade_connection(conn)
    assert conn.row_factory is sqlite3.Row
    assert conn.isolation_level == ""
    assert current_revision(conn) == HEAD
    conn.close()


def test_failed_migration_rolls_back(tmp_path, monkeypatch):
    """Koko upgrade on yksi transaktio: virhe ei jätä kantaa puolitiehen."""
    import services
    # Rikkoo services-taulun CHECK-ehdon revisiossa 0002
    monkeypatch.setattr(services, "SERVICES", [("999", "RIKKI", "lisat", "bad")])
    path = str(tmp_path / "fail.db")
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        upgrade_db(path)
    conn = sqlite3.connect(path)
    assert _tables(conn) == set()  # myös 0001:n taulut peruttiin
    conn.close()


def test_alembic_cli_upgrade(tmp_path):
    """`alembic -x db=polku upgrade head` ja FREIGHT_DB_PATH toimivat CLI:stä."""
    env = {k: v for k, v in os.environ.items() if k != db_config.DB_PATH_ENV}
    target = str(tmp_path / "cli.db")
    subprocess.run([sys.executable, "-m", "alembic", "-x", f"db={target}", "upgrade", "head"],
                   cwd=BACKEND_DIR, env=env, check=True, capture_output=True)
    conn = sqlite3.connect(target)
    assert current_revision(conn) == HEAD
    conn.close()

    env_target = str(tmp_path / "env.db")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                   cwd=BACKEND_DIR, env={**env, db_config.DB_PATH_ENV: env_target},
                   check=True, capture_output=True)
    conn = sqlite3.connect(env_target)
    assert current_revision(conn) == HEAD
    conn.close()


# ── 0003: rahakentät kokonaisluvuiksi ─────────────────────────────────

MONEY_COLUMNS = {
    "costs": {"amount_cents"},
    "trailers": {"leasing_rate_cents", "rental_rate_cents"},
    "ferry_rates": {"price_cents"},
    "km_rates": {"domestic_rate_e4", "continent_rate_e4"},
    "surcharge_rates": {"rate_e4", "min_amount_cents", "max_amount_cents"},
    "customer_rate_cards": {"freight_price_cents"},
    "customer_billing_rules": {"rate_e4"},
}
OLD_MONEY_COLUMNS = {"amount", "leasing_rate", "rental_rate", "price", "domestic_rate",
                     "continent_rate", "rate", "min_amount", "max_amount", "freight_price"}


def _types(conn, table):
    return {r[1]: r[2] for r in conn.execute(f"PRAGMA table_info({table})")}


def test_money_columns_are_integer(tmp_path):
    path = str(tmp_path / "head.db")
    upgrade_db(path)
    conn = sqlite3.connect(path)
    for table, cols in MONEY_COLUMNS.items():
        types = _types(conn, table)
        assert {c: types[c] for c in cols} == {c: "INTEGER" for c in cols}, table
        assert not OLD_MONEY_COLUMNS & set(types), table
    conn.close()


def test_money_migration_converts_legacy_values(tmp_path):
    conn = _pre_alembic_db(str(tmp_path / "legacy.db"))
    upgrade_connection(conn)
    assert current_revision(conn) == HEAD
    assert conn.execute("SELECT id, amount_cents FROM costs ORDER BY id").fetchall() == [
        (5, 30),      # 0.1 + 0.2 = 0.30000000000000004 → 0,30 €
        (6, 268),     # 2.675 (float 2.67499999…) → 2,68 € (ROUND_HALF_UP desimaalina)
        (10, 27550),  # 275.5 → 275,50 €
    ]
    assert conn.execute(
        "SELECT leasing_rate_cents, rental_rate_cents FROM trailers").fetchone() == (3550, 5400)
    assert conn.execute(
        "SELECT domestic_rate_e4, continent_rate_e4 FROM km_rates").fetchone() == (18500, 22000)
    assert conn.execute("SELECT price_cents FROM ferry_rates").fetchone() == (105000,)
    assert conn.execute(
        "SELECT rate_type, rate_e4, min_amount_cents, max_amount_cents FROM surcharge_rates "
        "ORDER BY id").fetchall() == [("per_100kg", 6000, 1500, None), ("percent", 123450, None, None)]
    assert conn.execute(
        "SELECT freight_price_cents FROM customer_rate_cards").fetchone() == (199999,)
    assert conn.execute(
        "SELECT service_code, rate_e4 FROM customer_billing_rules ORDER BY id").fetchall() == [
        ("510", 50000), ("230", None)]
    # Kaikki rahat tallessa kokonaislukuina
    for table, cols in MONEY_COLUMNS.items():
        for col in cols:
            kinds = {r[0] for r in conn.execute(f"SELECT DISTINCT typeof({col}) FROM {table}")}
            assert kinds <= {"integer", "null"}, (table, col, kinds)
    conn.close()


def test_money_migration_keeps_ids_indexes_and_sequence(tmp_path):
    conn = _pre_alembic_db(str(tmp_path / "legacy.db"))
    upgrade_connection(conn)
    # Poistetun rivin id:tä (9) ei käytetä uudelleen eikä mitään ennen 10:tä
    new_id = conn.execute(
        "INSERT INTO costs (trip_id, cost_code, description, amount_cents) "
        "VALUES (1, '799', 'UUSI', 100)").lastrowid
    assert new_id == 11
    indexes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"idx_surcharge_rates_lookup", "idx_customer_rate_cards_lookup",
            "idx_customer_billing_rules_lookup"} <= indexes
    conn.close()


def test_money_migration_downgrade_and_upgrade_again(tmp_path):
    from db_migrate import downgrade_connection
    conn = _pre_alembic_db(str(tmp_path / "legacy.db"))
    upgrade_connection(conn)
    after_upgrade = _schema(conn), _data(conn)
    downgrade_connection(conn, "0002")
    assert current_revision(conn) == "0002"
    assert _types(conn, "costs")["amount"] == "REAL"
    assert conn.execute("SELECT amount FROM costs ORDER BY id").fetchall() == [
        (0.3,), (2.68,), (275.5,)]
    upgrade_connection(conn)
    assert (_schema(conn), _data(conn)) == after_upgrade
    conn.close()


def test_money_migration_rejects_non_numeric_value(tmp_path):
    """Roskaa rahasarakkeessa (vanha km_rates-API ei validoinut) → migraatio
    keskeytyy eikä kantaa jätetä puolitiehen."""
    path = str(tmp_path / "bad.db")
    conn = _pre_alembic_db(path)
    conn.execute("UPDATE km_rates SET domestic_rate = 'abc'")
    conn.commit()
    with pytest.raises(ValueError, match="km_rates.domestic_rate"):
        upgrade_connection(conn)
    assert current_revision(conn) is None  # baselinekin peruttiin
    assert _types(conn, "costs")["amount"] == "REAL"
    conn.close()


def test_money_column_rejects_float(tmp_path):
    path = str(tmp_path / "check.db")
    upgrade_db(path)
    conn = sqlite3.connect(path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO costs (trip_id, cost_code, description, amount_cents) "
                     "VALUES (1, '120', 'X', 10.5)")
    conn.execute("INSERT INTO costs (trip_id, cost_code, description, amount_cents) "
                 "VALUES (1, '120', 'X', 1050)")
    conn.close()


# ── 0004: vetäjärekisteri (trucks → tractors) ─────────────────────────

def _db_at_0003(path):
    """Kanta revisiossa 0003: vanha trucks-taulu, tripit truck_plate-tekstillä."""
    conn = sqlite3.connect(path)
    upgrade_connection(conn, "0003")
    conn.executemany(
        "INSERT INTO carriers (id, name, country, city) VALUES (?, ?, 'FI', 'Demola')",
        [(1, "Demo Alfa Oy"), (2, "Demo Beta Oy")])
    conn.executemany(
        "INSERT INTO trucks (id, plate_number, carrier_id, status) VALUES (?, ?, ?, ?)",
        [(1, "AAA-001", 1, "Vapaa"), (2, "aaa-002 ", 1, "Ajossa"),
         (4, "BBB-001", 2, "Huollossa"), (5, "AAA-001", 1, "Vapaa")])  # 5 = saman carrierin tupla
    conn.executemany(
        "INSERT INTO trips (id, trip_id, status, carrier_id, truck_plate) VALUES (?, ?, ?, ?, ?)",
        [(1, "TRP-M-1", "Suunniteltu", 1, "AAA-001"),
         (2, "TRP-M-2", "Laskutettu", 1, "AAA-002"),      # normalisoitu osuma
         (3, "TRP-M-3", "Vahvistettu", 1, "BBB-001"),     # eri carrier → ei linkkiä
         (4, "TRP-M-4", "Suunniteltu", 2, None)])
    conn.executemany(
        "INSERT INTO trailers (id, plate_number, identifier, trailer_type) VALUES (?, ?, ?, ?)",
        [(1, "T-1", "T-1", "Umpikaappi"), (2, "T-2", "T-2", "Megatrailer"),
         (3, "T-3", "T-3", "Sivuaukeava")])
    conn.commit()
    return conn


def test_tractors_migration_moves_trucks(tmp_path):
    conn = _db_at_0003(str(tmp_path / "m4.db"))
    upgrade_connection(conn)
    assert current_revision(conn) == HEAD
    assert "trucks" not in _tables(conn)
    assert conn.execute(
        "SELECT id, registration_number, carrier_id, vehicle_type, status FROM tractors ORDER BY id"
    ).fetchall() == [
        (1, "AAA-001", 1, "vetoauto", "aktiivinen"),
        (2, "AAA-002", 1, "vetoauto", "aktiivinen"),
        (4, "BBB-001", 2, "vetoauto", "huollossa"),
    ]
    assert conn.execute("SELECT id, tractor_id, truck_plate FROM trips ORDER BY id").fetchall() == [
        (1, 1, "AAA-001"), (2, 2, "AAA-002"), (3, None, "BBB-001"), (4, None, None)]
    assert conn.execute(
        "SELECT id, temperature_controlled, adr, tail_lift, crane FROM trailers ORDER BY id"
    ).fetchall() == [(1, 1, 0, 0, 0), (2, 0, 0, 0, 0), (3, 1, 0, 0, 0)]
    # AUTOINCREMENT jatkuu trucks-taulun laskurista (tupla id 5 ei palaa käyttöön)
    new_id = conn.execute(
        "INSERT INTO tractors (registration_number, carrier_id) VALUES ('NEW-1', 1)").lastrowid
    assert new_id == 6
    indexes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"idx_tractors_carrier", "idx_trips_tractor"} <= indexes
    conn.close()


def test_tractors_migration_rejects_plate_on_two_carriers(tmp_path):
    conn = _db_at_0003(str(tmp_path / "conflict.db"))
    conn.execute("INSERT INTO trucks (plate_number, carrier_id) VALUES ('bbb-001', 1)")
    conn.commit()
    with pytest.raises(ValueError, match="BBB-001"):
        upgrade_connection(conn)
    assert current_revision(conn) == "0003"
    assert "trucks" in _tables(conn) and "tractors" not in _tables(conn)
    conn.close()


def test_tractors_migration_downgrade_and_upgrade_again(tmp_path):
    from db_migrate import downgrade_connection
    conn = _db_at_0003(str(tmp_path / "m4.db"))
    upgrade_connection(conn)
    conn.execute("UPDATE tractors SET status = 'poistettu' WHERE id = 4")
    conn.commit()
    downgrade_connection(conn, "0003")
    assert current_revision(conn) == "0003"
    assert "tractors" not in _tables(conn)
    assert "tractor_id" not in _types(conn, "trips")
    assert not {"adr", "temperature_controlled", "tail_lift", "crane"} & set(_types(conn, "trailers"))
    assert conn.execute("SELECT id, plate_number, carrier_id, status FROM trucks ORDER BY id").fetchall() == [
        (1, "AAA-001", 1, "Vapaa"), (2, "AAA-002", 1, "Vapaa"), (4, "BBB-001", 2, "Poistettu")]
    upgrade_connection(conn)
    assert conn.execute("SELECT id, registration_number, status FROM tractors ORDER BY id").fetchall() == [
        (1, "AAA-001", "aktiivinen"), (2, "AAA-002", "aktiivinen"), (4, "BBB-001", "poistettu")]
    assert conn.execute("SELECT id, tractor_id FROM trips ORDER BY id").fetchall() == [
        (1, 1), (2, 2), (3, None), (4, None)]
    conn.close()


# ── Varmuuskopio ennen migraatiota ────────────────────────────────────

def _backups(tmp_path):
    return sorted(p.name for p in tmp_path.iterdir() if ".bak-" in p.name)


def test_upgrade_db_backs_up_pending_database(tmp_path):
    path = str(tmp_path / "old.db")
    _db_at_0003(path).close()
    upgrade_db(path)
    backups = _backups(tmp_path)
    assert len(backups) == 1 and backups[0].startswith("old.db.bak-0003-")
    backup = sqlite3.connect(str(tmp_path / backups[0]))
    assert current_revision(backup) == "0003"
    assert backup.execute("SELECT COUNT(*) FROM trucks").fetchone()[0] == 4
    backup.close()
    # Kanta on jo headissa: uutta kopiota ei tehdä
    upgrade_db(path)
    assert len(_backups(tmp_path)) == 1


def test_upgrade_db_skips_backup_for_new_database(tmp_path):
    upgrade_db(str(tmp_path / "new.db"))
    assert _backups(tmp_path) == []


def test_alembic_cli_backs_up_pending_database(tmp_path):
    target = str(tmp_path / "cli-old.db")
    _db_at_0003(target).close()
    env = {k: v for k, v in os.environ.items() if k != db_config.DB_PATH_ENV}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-x", f"db={target}", "upgrade", "head"],
        cwd=BACKEND_DIR, env=env, check=True, capture_output=True, text=True)
    assert "Varmuuskopio ennen migraatiota" in result.stdout
    assert [b for b in _backups(tmp_path) if b.startswith("cli-old.db.bak-0003-")]


# ── 0005: trailerien yksikäsitteisyys, huoltohistoria id:hen ──────────

def _db_at_0004(path, trailers, maintenance=()):
    """Kanta revisiossa 0004. trailers: (id, plate, identifier, status);
    maintenance: (id, rekisteriteksti)."""
    conn = sqlite3.connect(path)
    upgrade_connection(conn, "0004")
    conn.executemany(
        "INSERT INTO trailers (id, plate_number, identifier, trailer_type, status) "
        "VALUES (?, ?, ?, 'Pressutrailer', ?)", trailers)
    conn.executemany(
        "INSERT INTO trailer_maintenance (id, trailer_id, maintenance_type, date, notes) "
        "VALUES (?, ?, 'INSPECTION', '2026-01-15', 'Demo')", maintenance)
    conn.commit()
    return conn


def _snapshot(conn):
    return _schema(conn), _data(conn), current_revision(conn)


def test_trailer_migration_links_maintenance_to_ids(tmp_path):
    conn = _db_at_0004(str(tmp_path / "t5.db"),
                       [(1, "abc-1 ", "T-1", "Vapaa"), (2, "DEF-2", "T-2", "Käytössä"),
                        (5, "GHI-3", "T-3", None)],
                       [(10, "ABC-1"), (11, "abc-1"), (12, " def-2"), (13, "DEF-2")])
    upgrade_connection(conn)
    assert current_revision(conn) == HEAD
    assert conn.execute("SELECT id, plate_number, identifier, status FROM trailers ORDER BY id"
                        ).fetchall() == [(1, "ABC-1", "T-1", "Vapaa"), (2, "DEF-2", "T-2", "Käytössä"),
                                         (5, "GHI-3", "T-3", "Vapaa")]
    assert conn.execute("SELECT id, trailer_id, typeof(trailer_id) FROM trailer_maintenance "
                        "ORDER BY id").fetchall() == [
        (10, 1, "integer"), (11, 1, "integer"), (12, 2, "integer"), (13, 2, "integer")]
    trailer_cols = {r[1]: r for r in conn.execute("PRAGMA table_info(trailers)")}
    assert trailer_cols["plate_number"][3] == 0       # rekisteri valinnainen
    assert trailer_cols["identifier"][3] == 1         # tunniste pakollinen
    # AUTOINCREMENT jatkuu, rekisteritön vaihtokori sallittu, tuplat estetty
    swap_id = conn.execute("INSERT INTO trailers (identifier, trailer_type) "
                           "VALUES ('VK-1', 'Pressutrailer')").lastrowid
    assert swap_id == 6
    conn.execute("INSERT INTO trailers (identifier, trailer_type) VALUES ('VK-2', 'Pressutrailer')")
    for sql in ("INSERT INTO trailers (plate_number, identifier, trailer_type) VALUES ('Abc-1', 'X', 'Megatrailer')",
                "INSERT INTO trailers (identifier, trailer_type) VALUES ('t-1', 'Megatrailer')",
                "INSERT INTO trailers (identifier, trailer_type, status) VALUES ('Y', 'Megatrailer', 'Romu')",
                "INSERT INTO trailer_maintenance (trailer_id, maintenance_type, date) VALUES ('ABC-1', 'OTHER', '2026-01-01')"):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql)
    conn.close()


def test_trailer_migration_fills_identifier_from_plate(tmp_path, capsys):
    conn = _db_at_0004(str(tmp_path / "fill.db"),
                       [(1, "AAA-1", "", "Vapaa"), (2, "BBB-2", "  ", "Vapaa"), (3, "CCC-3", "C-3", "Vapaa")])
    upgrade_connection(conn)
    assert conn.execute("SELECT id, identifier FROM trailers ORDER BY id").fetchall() == [
        (1, "AAA-1"), (2, "BBB-2"), (3, "C-3")]
    out = capsys.readouterr().out
    assert "id=1 tyhjä tunniste täytetty rekisterillä AAA-1" in out
    assert "id=2 tyhjä tunniste täytetty rekisterillä BBB-2" in out
    assert "id=3" not in out
    conn.close()


@pytest.mark.parametrize("trailers,expected", [
    # rekisterituplat (kirjainkoosta ja välilyönneistä riippumatta)
    ([(1, "DUP-1", "A", "Vapaa"), (2, " dup-1", "B", "Vapaa")], "Rekisterinumero DUP-1 on usealla trailerilla: id=1, id=2"),
    # tunnistetuplat
    ([(1, "P-1", "Sama", "Vapaa"), (2, "P-2", "SAMA", "Vapaa")], "Tunniste Sama on usealla trailerilla: id=1, id=2"),
    # täyttö törmää olemassa olevaan tunnisteeseen → todellinen tupla
    ([(1, "X-1", "", "Vapaa"), (2, "X-2", "X-1", "Vapaa")],
     "Tunniste X-1 on usealla trailerilla: id=1 (tunniste täytetty rekisteristä), id=2"),
    # tuntematon status
    ([(1, "S-1", "S-1", "Romutettu")], "tuntematon status 'Romutettu'"),
])
def test_trailer_migration_stops_on_conflicts(tmp_path, trailers, expected):
    conn = _db_at_0004(str(tmp_path / "dup.db"), trailers)
    before = _snapshot(conn)
    with pytest.raises(ValueError, match="Migraatio 0005 pysähtyi") as err:
        upgrade_connection(conn)
    assert expected in str(err.value)
    assert _snapshot(conn) == before  # kanta ennallaan (revisio 0004)
    conn.close()


def test_trailer_migration_stops_on_orphan_maintenance(tmp_path):
    conn = _db_at_0004(str(tmp_path / "orphan.db"),
                       [(1, "OK-1", "OK-1", "Vapaa")],
                       [(20, "OK-1"), (21, "POISTETTU-9"), (22, "EI-OLE")])
    before = _snapshot(conn)
    with pytest.raises(ValueError) as err:
        upgrade_connection(conn)
    message = str(err.value)
    assert "Orpoja huoltorivejä" in message
    assert "trailer_maintenance id=21" in message and "'POISTETTU-9'" in message
    assert "trailer_maintenance id=22" in message
    assert "id=20" not in message
    assert "DELETE FROM trailer_maintenance WHERE id IN (21, 22);" in message
    assert _snapshot(conn) == before

    # Virheilmoituksen siivous-SQL kelpaa sellaisenaan
    cleanup = next(line.strip() for line in message.splitlines() if line.strip().startswith("DELETE"))
    conn.execute(cleanup)
    conn.commit()
    upgrade_connection(conn)
    assert current_revision(conn) == HEAD
    assert conn.execute("SELECT id, trailer_id FROM trailer_maintenance").fetchall() == [(20, 1)]
    conn.close()


def test_trailer_migration_downgrade_and_upgrade_again(tmp_path):
    from db_migrate import downgrade_connection
    conn = _db_at_0004(str(tmp_path / "down.db"),
                       [(1, "ABC-1", "T-1", "Vapaa"), (2, "DEF-2", "T-2", "Huollossa")],
                       [(10, "ABC-1"), (11, "DEF-2")])
    upgrade_connection(conn)
    conn.execute("UPDATE trailers SET status = 'Poistettu' WHERE id = 2")
    conn.commit()
    after_upgrade = _snapshot(conn)
    downgrade_connection(conn, "0004")
    assert current_revision(conn) == "0004"
    assert conn.execute("SELECT id, trailer_id FROM trailer_maintenance ORDER BY id").fetchall() == [
        (10, "ABC-1"), (11, "DEF-2")]
    assert conn.execute("SELECT status FROM trailers WHERE id = 2").fetchone() == ("Poistettu",)
    upgrade_connection(conn)
    assert _snapshot(conn) == after_upgrade
    conn.close()


def test_trailer_downgrade_stops_on_trailers_without_plate(tmp_path):
    from db_migrate import downgrade_connection
    conn = _db_at_0004(str(tmp_path / "swap.db"), [(1, "ABC-1", "T-1", "Vapaa")], [(10, "ABC-1")])
    upgrade_connection(conn)
    conn.execute("INSERT INTO trailers (id, identifier, trailer_type) VALUES (7, 'VK-7', 'Pressutrailer')")
    conn.commit()
    before = _snapshot(conn)
    with pytest.raises(ValueError, match=r"Downgrade 0005 → 0004 pysähtyi.*1 traileria ilman "
                                         r"rekisterinumeroa \(id=7 \(VK-7\)\)"):
        downgrade_connection(conn, "0004")
    assert _snapshot(conn) == before
    assert current_revision(conn) == "0005"
    conn.close()

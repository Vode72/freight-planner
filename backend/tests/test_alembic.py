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
    "trips", "orders", "costs", "trailers", "carriers", "trucks", "customers",
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


def _pre_alembic_db(path, revision):
    """Kanta sellaisena kuin vanhat skriptit sen jättivät: skeema + demodata,
    ei alembic_version-taulua."""
    conn = sqlite3.connect(path)
    upgrade_connection(conn, revision)
    seed_demo_data(conn)
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
    conn = _pre_alembic_db(str(tmp_path / "legacy.db"), "0002")
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

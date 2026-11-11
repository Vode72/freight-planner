"""Tietokantapolun ja käynnistyksen testit (issue #14)."""
import os
import sqlite3
import subprocess
import sys

import pytest

import db_config
from reset_demo import reset_demo

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEC_COLS = {"loading_started_at", "loading_completed_at",
            "delivery_started_at", "delivery_completed_at", "delivered_at"}


def _run_python(code, env_overrides, cwd=BACKEND_DIR):
    env = {k: v for k, v in os.environ.items() if k != db_config.DB_PATH_ENV}
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-c", code], cwd=cwd, env=env,
        capture_output=True, text=True, check=True,
    )


def _legacy_db(path):
    """Vanha kanta ilman FEC-sarakkeita: migrate_db() lisäisi ne."""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE trips (id INTEGER PRIMARY KEY, trip_id TEXT)")
    conn.commit()
    conn.close()


def _trip_columns(path):
    conn = sqlite3.connect(path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(trips)")}
    conn.close()
    return cols


# ── db_config ─────────────────────────────────────────────────────────

def test_default_db_path_is_backend_freight_db(monkeypatch):
    monkeypatch.delenv(db_config.DB_PATH_ENV, raising=False)
    assert db_config.get_db_path() == os.path.join(BACKEND_DIR, "freight.db")


def test_env_var_overrides_db_path(monkeypatch, tmp_path):
    target = str(tmp_path / "custom.db")
    monkeypatch.setenv(db_config.DB_PATH_ENV, target)
    assert db_config.get_db_path() == target


def test_empty_env_var_falls_back_to_default(monkeypatch):
    monkeypatch.setenv(db_config.DB_PATH_ENV, "")
    assert db_config.get_db_path() == db_config.DEFAULT_DB_PATH


def test_app_uses_env_db_path(tmp_path):
    target = str(tmp_path / "env.db")
    out = _run_python("import app; print(app.DB_NAME)", {db_config.DB_PATH_ENV: target})
    assert out.stdout.strip() == target


def test_default_path_independent_of_cwd(tmp_path):
    code = f"import sys; sys.path.insert(0, {BACKEND_DIR!r}); import app; print(app.DB_NAME)"
    out = _run_python(code, {}, cwd=str(tmp_path))
    assert out.stdout.strip() == os.path.join(BACKEND_DIR, "freight.db")


# ── migrate_db ei aja importissa ──────────────────────────────────────

def test_import_app_does_not_migrate(tmp_path):
    # Kanta on sekä ympäristömuuttujan että relatiivisen "freight.db":n
    # kohteena, joten import ei saa muuttaa sitä kummallakaan polulla.
    target = str(tmp_path / "freight.db")
    _legacy_db(target)
    before = os.path.getmtime(target), open(target, "rb").read()
    code = f"import sys; sys.path.insert(0, {BACKEND_DIR!r}); import app"
    _run_python(code, {db_config.DB_PATH_ENV: target}, cwd=str(tmp_path))
    assert (os.path.getmtime(target), open(target, "rb").read()) == before
    assert not FEC_COLS & _trip_columns(target)


def test_import_app_does_not_create_db(tmp_path):
    target = str(tmp_path / "missing.db")
    _run_python("import app", {db_config.DB_PATH_ENV: target})
    assert not os.path.exists(target)


def test_import_app_does_not_touch_default_db():
    default = db_config.DEFAULT_DB_PATH
    existed = os.path.exists(default)
    before = (os.path.getmtime(default), open(default, "rb").read()) if existed else None
    _run_python("import app", {})
    if existed:
        assert (os.path.getmtime(default), open(default, "rb").read()) == before
    else:
        assert not os.path.exists(default)


def test_migrate_db_with_explicit_path(tmp_path):
    import app as flask_app
    target = str(tmp_path / "legacy.db")
    _legacy_db(target)
    flask_app.migrate_db(target)
    assert FEC_COLS <= _trip_columns(target)


# ── reset_demo ────────────────────────────────────────────────────────

EXPECTED_TABLES = {
    "trips", "orders", "costs", "trailers", "carriers", "tractors", "customers",
    "country_restrictions", "terminals", "trailer_maintenance", "km_rates",
    "ferry_rates", "settings", "services", "surcharge_rates",
    "customer_rate_cards", "customer_billing_rules",
}


def _counts(path):
    conn = sqlite3.connect(path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in EXPECTED_TABLES & tables}
    conn.close()
    return tables, counts


def test_reset_demo_builds_full_db(tmp_path):
    target = str(tmp_path / "demo.db")
    reset_demo(target)
    tables, counts = _counts(target)
    assert EXPECTED_TABLES <= tables
    assert counts["trips"] == 7
    assert counts["orders"] == 12
    assert counts["carriers"] == 6
    assert counts["trailers"] == 12
    assert counts["terminals"] == 16
    assert all(counts[t] > 0 for t in ("costs", "customers", "services",
                                       "surcharge_rates", "customer_rate_cards"))
    assert FEC_COLS <= _trip_columns(target)


def test_reset_demo_is_clean_and_repeatable(tmp_path):
    target = str(tmp_path / "demo.db")
    reset_demo(target)
    _, first = _counts(target)

    conn = sqlite3.connect(target)
    conn.execute("INSERT INTO customers (name, country) VALUES ('Ylimääräinen Demo Oy', 'FI')")
    conn.execute("INSERT INTO surcharge_rates (service_code, cost_type, rate_type, rate_e4, valid_from) "
                 "VALUES ('600', 'cost', 'fixed', 1, '2026-01-01')")
    conn.commit()
    conn.close()

    reset_demo(target)
    _, second = _counts(target)
    assert first == second


def test_reset_demo_cli_uses_env_path(tmp_path):
    target = str(tmp_path / "cli.db")
    _run_python("import runpy; runpy.run_path('reset_demo.py', run_name='__main__')",
                {db_config.DB_PATH_ENV: target})
    tables, counts = _counts(target)
    assert EXPECTED_TABLES <= tables and counts["trips"] == 7

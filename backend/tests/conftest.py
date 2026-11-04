import hashlib
import os
import sqlite3
import tempfile

import pytest

# Testit eivät koskaan saa koskea backend/freight.db:hen. Oletuspolku
# ohjataan väliaikaiseen hakemistoon ennen kuin app-moduuli importataan;
# fixturet asettavat lisäksi DB_NAME:n tmp_path-kantaan.
_SESSION_TMP = tempfile.mkdtemp(prefix="freight-tests-")
os.environ["FREIGHT_DB_PATH"] = os.path.join(_SESSION_TMP, "unused.db")

from db_config import DEFAULT_DB_PATH  # noqa: E402

import app as flask_app  # noqa: E402
from init_db import create_schema, seed_demo_data
from migrate_restrictions import run_migration as run_restrictions
from migrate_hallinta import run_migration as run_hallinta
from migrate_settings import run_migration as run_settings
from migrate_services import run_migration as run_services
from migrate_surcharges import run_migration as run_surcharges
from migrate_customer_pricing import run_migration as run_customer_pricing


def _build_test_db(db_path, with_seed=False):
    """Create schema (+ optionally seed demo data) and run all migrations."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    if with_seed:
        seed_demo_data(conn)
    conn.commit()
    conn.close()
    run_restrictions(db_path)
    run_hallinta(db_path)
    run_settings(db_path)
    run_services(db_path)
    run_surcharges(db_path)
    run_customer_pricing(db_path)


@pytest.fixture
def client(tmp_path):
    """Flask test client backed by a fresh empty-schema DB (no demo data)."""
    db_path = str(tmp_path / "test.db")
    _build_test_db(db_path)
    flask_app.DB_NAME = db_path
    with flask_app.app.test_client() as c:
        yield c, db_path


@pytest.fixture
def demo_client(tmp_path):
    """Flask test client backed by full demo data + all migrations."""
    db_path = str(tmp_path / "test.db")
    _build_test_db(db_path, with_seed=True)
    flask_app.DB_NAME = db_path
    with flask_app.app.test_client() as c:
        yield c, db_path


def _file_fingerprint(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return os.path.getmtime(path), hashlib.sha256(f.read()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def guard_real_db():
    """Varmistaa, ettei testiajo luo tai muuta backend/freight.db:tä."""
    before = _file_fingerprint(DEFAULT_DB_PATH)
    yield
    assert _file_fingerprint(DEFAULT_DB_PATH) == before, (
        "Testiajo loi tai muutti tiedoston backend/freight.db"
    )

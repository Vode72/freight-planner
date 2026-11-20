"""Alembic-migraatiot sovelluksesta käsin.

Skeema elää vain Alembic-revisioissa (backend/migrations/versions).
Tämä moduuli ajaa ne joko kantatiedostoon (upgrade_db) tai jo avattuun
sqlite3-yhteyteen (upgrade_connection, esim. testien muistikanta).

Komentoriviltä (backend-hakemistossa):

    alembic upgrade head                      # FREIGHT_DB_PATH / backend/freight.db
    alembic -x db=polku.db upgrade head       # kohde annettuna

Ennen upgradea olemassa olevasta kantatiedostosta otetaan varmuuskopio,
jos siinä on ajamattomia revisioita (backup_if_pending): tiedosto
``<kanta>.bak-<revisio>-<aikaleima>`` samaan hakemistoon. Kopio tehdään
SQLiten backup-rajapinnalla, joten se on eheä myös WAL-tilassa.

Koko upgrade ajetaan yhtenä transaktiona: pysqlite ei oletuksena aloita
transaktiota DDL-lauseille, joten BEGIN annetaan itse (SQLAlchemyn
dokumentoima resepti). Epäonnistunut migraatio ei jätä kantaa puolitiehen.
"""
import os
import sqlite3
from datetime import datetime

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
MIGRATIONS_DIR = os.path.join(BACKEND_DIR, "migrations")


class _BorrowedConnection:
    """sqlite3-yhteys SQLAlchemylle lainaan: close() ei sulje oikeaa yhteyttä."""

    def __init__(self, conn):
        object.__setattr__(self, "_conn", conn)

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __setattr__(self, name, value):
        setattr(self._conn, name, value)


def make_engine(creator):
    """SQLite-engine, jonka transaktio kattaa myös DDL:n."""
    engine = create_engine(
        "sqlite://", creator=creator, poolclass=StaticPool,
        pool_reset_on_return=None,
    )

    @event.listens_for(engine, "connect")
    def _no_implicit_transactions(dbapi_conn, _record):
        dbapi_conn.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin(conn):
        conn.exec_driver_sql("BEGIN")

    return engine


def alembic_config():
    cfg = Config()
    cfg.set_main_option("script_location", MIGRATIONS_DIR)
    return cfg


def _run(conn, fn, *args):
    """Ajaa Alembic-komennon annetulla sqlite3-yhteydellä.

    Yhteyden isolation_level ja row_factory palautetaan ennalleen.
    Avoin transaktio commitoidaan ensin, jotta BEGIN onnistuu.
    """
    if conn.in_transaction:
        conn.commit()
    saved = conn.isolation_level, conn.row_factory
    conn.row_factory = None
    engine = make_engine(lambda: _BorrowedConnection(conn))
    try:
        with engine.connect() as sa_conn:
            cfg = alembic_config()
            cfg.attributes["connection"] = sa_conn
            fn(cfg, *args)
    finally:
        conn.isolation_level, conn.row_factory = saved


def sync_reference_data(conn):
    """Palvelukoodiston synkronointi koodista (services.SERVICES).

    Idempotentti: uudet koodit lisätään, nimet päivitetään ja vanhat
    koodit (401, 831) yhdistetään. Ajetaan jokaisen upgraden jälkeen.
    """
    from services import run_services_migration
    changed = run_services_migration(conn)
    conn.commit()
    return changed


def upgrade_connection(conn, revision="head"):
    """Ajaa migraatiot avoimeen sqlite3-yhteyteen (+ koodiston synkronointi)."""
    _run(conn, command.upgrade, revision)
    if revision == "head":
        sync_reference_data(conn)


def downgrade_connection(conn, revision):
    _run(conn, command.downgrade, revision)


def head_revision():
    from alembic.script import ScriptDirectory
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def backup_if_pending(db_path):
    """Varmuuskopio kantatiedostosta ennen migraatiota.

    Kopio tehdään vain, kun tiedosto on olemassa, siinä on tauluja ja sen
    revisio ei ole head (eli upgrade muuttaisi sitä). Palauttaa kopion
    polun tai None. Uutta tai tyhjää kantaa ei kopioida.
    """
    if not db_path or not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        return None
    src = sqlite3.connect(db_path)
    try:
        has_tables = src.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()
        current = current_revision(src)
        if not has_tables or current == head_revision():
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{db_path}.bak-{current or 'pre-alembic'}-{stamp}"
        n = 1
        while os.path.exists(backup_path):
            n += 1
            backup_path = f"{db_path}.bak-{current or 'pre-alembic'}-{stamp}-{n}"
        dst = sqlite3.connect(backup_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
        return backup_path
    finally:
        src.close()


def upgrade_db(db_path, revision="head", backup=True):
    """Ajaa migraatiot kantatiedostoon. Luo tiedoston, jos sitä ei ole.

    backup=True: olemassa olevasta, migroimattomasta kannasta otetaan ensin
    varmuuskopio (backup_if_pending).
    """
    if backup:
        backup_path = backup_if_pending(db_path)
        if backup_path:
            print(f"Varmuuskopio ennen migraatiota: {backup_path}")
    conn = sqlite3.connect(db_path)
    try:
        upgrade_connection(conn, revision)
    finally:
        conn.close()


def downgrade_db(db_path, revision):
    conn = sqlite3.connect(db_path)
    try:
        downgrade_connection(conn, revision)
    finally:
        conn.close()


def current_revision(conn):
    """Kannan Alembic-revisio tai None (ei migroitu)."""
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'"
    ).fetchone()
    if not exists:
        return None
    row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    return row[0] if row else None

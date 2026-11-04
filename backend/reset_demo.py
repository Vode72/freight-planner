"""Puhdas demokanta yhdellä komennolla.

    python reset_demo.py              # kohde: FREIGHT_DB_PATH tai backend/freight.db
    python reset_demo.py polku.db     # kohde annettuna

Poistaa vanhan kantatiedoston ja luo uuden: skeema + demodata + kaikki
migraatiot + käynnistysmigraatio (migrate_db). Kaikki data on keksittyä.
"""
import os
import sqlite3
import sys

from db_config import get_db_path
from init_db import create_schema, seed_demo_data
from migrate_restrictions import run_migration as run_restrictions
from migrate_hallinta import run_migration as run_hallinta
from migrate_settings import run_migration as run_settings
from migrate_services import run_migration as run_services
from migrate_surcharges import run_migration as run_surcharges
from migrate_customer_pricing import run_migration as run_customer_pricing


def reset_demo(db_path):
    for suffix in ("", "-wal", "-shm", "-journal"):
        if os.path.exists(db_path + suffix):
            os.remove(db_path + suffix)

    conn = sqlite3.connect(db_path)
    create_schema(conn)
    seed_demo_data(conn)
    conn.commit()
    conn.close()

    run_restrictions(db_path)
    run_hallinta(db_path)
    run_settings(db_path)
    run_services(db_path)
    run_surcharges(db_path)
    run_customer_pricing(db_path)

    from app import migrate_db
    migrate_db(db_path)
    return db_path


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else get_db_path()
    reset_demo(target)
    print(f"Demokanta luotu: {os.path.abspath(target)}")

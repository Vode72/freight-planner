"""Puhdas demokanta yhdellä komennolla.

    python reset_demo.py              # kohde: FREIGHT_DB_PATH tai backend/freight.db
    python reset_demo.py polku.db     # kohde annettuna

Poistaa vanhan kantatiedoston ja luo uuden: Alembic-migraatiot
(alembic upgrade head) + demodata. Kaikki data on keksittyä.
"""
import os
import sqlite3
import sys

from db_config import get_db_path
from db_migrate import upgrade_db
from init_db import seed_demo_data


def reset_demo(db_path):
    for suffix in ("", "-wal", "-shm", "-journal"):
        if os.path.exists(db_path + suffix):
            os.remove(db_path + suffix)

    upgrade_db(db_path)
    conn = sqlite3.connect(db_path)
    seed_demo_data(conn)
    conn.commit()
    conn.close()
    return db_path


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else get_db_path()
    reset_demo(target)
    print(f"Demokanta luotu: {os.path.abspath(target)}")

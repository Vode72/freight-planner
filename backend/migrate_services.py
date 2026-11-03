import sqlite3

from services import SERVICES, run_services_migration


def run_migration(db_path):
    conn = sqlite3.connect(db_path)
    changed = run_services_migration(conn)
    conn.commit()
    conn.close()
    print(
        f"migrate_services.py valmis — {len(SERVICES)} palvelukoodia, "
        f"{changed} costs-riviä migroitu (401→400, 831→830)."
    )


if __name__ == "__main__":
    run_migration("freight.db")

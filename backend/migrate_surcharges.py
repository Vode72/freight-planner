import sqlite3

from surcharges import run_surcharges_migration


def run_migration(db_path):
    conn = sqlite3.connect(db_path)
    seeded = run_surcharges_migration(conn)
    conn.commit()
    conn.close()
    print(f"migrate_surcharges.py valmis — surcharge_rates, {seeded} demoriviä lisätty.")


if __name__ == "__main__":
    run_migration("freight.db")

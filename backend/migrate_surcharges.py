import sqlite3

from surcharges import (
    ensure_surcharge_rates, seed_surcharge_rates, migrate_fuel_rates,
)


def run_migration(db_path):
    conn = sqlite3.connect(db_path)
    ensure_surcharge_rates(conn)
    seeded = seed_surcharge_rates(conn)
    fuel = migrate_fuel_rates(conn)
    conn.commit()
    conn.close()
    print(f"migrate_surcharges.py valmis — surcharge_rates, {seeded} demoriviä lisätty, "
          f"{fuel} polttoainekerrointa siirretty fuel_rates-taulusta.")


if __name__ == "__main__":
    from db_config import get_db_path
    run_migration(get_db_path())

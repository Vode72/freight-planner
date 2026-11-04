import sqlite3

from customer_pricing import ensure_customer_pricing_tables, seed_customer_pricing


def run_migration(db_path):
    conn = sqlite3.connect(db_path)
    ensure_customer_pricing_tables(conn)
    cards, rules = seed_customer_pricing(conn)
    conn.commit()
    conn.close()
    print(f"migrate_customer_pricing.py valmis — customer_rate_cards ja "
          f"customer_billing_rules, {cards} hinnastoriviä ja {rules} lisäsääntöä lisätty.")


if __name__ == "__main__":
    run_migration("freight.db")

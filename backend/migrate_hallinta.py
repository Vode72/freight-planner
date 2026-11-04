import sqlite3
from datetime import date, timedelta


def run_migration(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(trailers)").fetchall()}
    new_trailer_cols = [
        ("inspection_date",                      "TEXT"),
        ("inspection_due",                       "TEXT"),
        ("refrigeration_service_date",           "TEXT"),
        ("refrigeration_service_due",            "TEXT"),
        ("refrigeration_service_interval_months", "INTEGER DEFAULT 6"),
        ("maintenance_notes",                    "TEXT"),
    ]
    for col, typedef in new_trailer_cols:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE trailers ADD COLUMN {col} {typedef}")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS trailer_maintenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trailer_id TEXT NOT NULL REFERENCES trailers(plate_number),
    maintenance_type TEXT NOT NULL,
    date TEXT NOT NULL,
    next_due TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS km_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    domestic_rate REAL NOT NULL,
    continent_rate REAL NOT NULL,
    notes TEXT
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS ferry_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route TEXT NOT NULL,
    price REAL NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    notes TEXT
)
""")

    trailers = cursor.execute("SELECT plate_number, trailer_type FROM trailers").fetchall()
    trailer_map = {t[0]: t[1] for t in trailers}

    cursor.execute("DELETE FROM trailer_maintenance")

    today = date.today()
    maintenance_rows = []

    for plate, days_ago, next_days in [
        ("URV-001", 365, 365),
        ("URV-002", 180, 545),
        ("SRV-001", 270, 460),
        ("CRT-001", 90, 640),
        ("HRV-001", 400, 330),
    ]:
        if plate in trailer_map:
            maintenance_rows.append((
                plate, "INSPECTION",
                (today - timedelta(days=days_ago)).isoformat(),
                (today + timedelta(days=next_days - days_ago)).isoformat(),
                "Katsastus OK",
            ))

    for plate, days_ago, next_days in [
        ("URV-001", 120, 180),
        ("URV-002", 30, 150),
        ("TRV-001", 200, -20),
    ]:
        ttype = trailer_map.get(plate, "")
        if "Umpikaappi" in ttype:
            maintenance_rows.append((
                plate, "REFRIGERATION",
                (today - timedelta(days=days_ago)).isoformat(),
                (today + timedelta(days=next_days)).isoformat(),
                "Kylmäkonehuolto suoritettu",
            ))

    cursor.executemany(
        "INSERT INTO trailer_maintenance (trailer_id, maintenance_type, date, next_due, notes) "
        "VALUES (?,?,?,?,?)",
        maintenance_rows,
    )

    if "HRV-001" in trailer_map:
        cursor.execute(
            "UPDATE trailers SET inspection_date='2025-05-01', inspection_due=? WHERE plate_number='HRV-001'",
            ((today - timedelta(days=20)).isoformat(),),
        )
    for plate, insp_date, delta in [
        ("URV-003", "2025-11-01", 18),
        ("CRT-002", "2025-11-15", 25),
        ("URV-001", "2025-06-01", 365 - 120),
        ("URV-002", "2025-12-01", 180),
        ("SRV-001", "2025-08-01", 90),
        ("CRT-001", "2026-01-15", 120),
    ]:
        if plate in trailer_map:
            cursor.execute(
                f"UPDATE trailers SET inspection_date=?, inspection_due=? WHERE plate_number=?",
                (insp_date, (today + timedelta(days=delta)).isoformat(), plate),
            )

    for plate, svc_date, delta, interval in [
        ("URV-001", "2025-12-01", 60, 6),
        ("URV-002", "2026-01-15", 15, 6),
        ("TRV-001", "2025-10-01", -20, 6),
        ("TRV-002", "2026-02-01", 95, 6),
    ]:
        if plate in trailer_map:
            cursor.execute(
                "UPDATE trailers SET refrigeration_service_date=?, refrigeration_service_due=?, "
                "refrigeration_service_interval_months=? WHERE plate_number=?",
                (svc_date, (today + timedelta(days=delta)).isoformat(), interval, plate),
            )

    cursor.execute("DELETE FROM km_rates")
    cursor.execute(
        "INSERT INTO km_rates (valid_from, valid_to, domestic_rate, continent_rate, notes) "
        "VALUES ('2026-01-01', NULL, 1.85, 2.20, 'Perushinnoittelu 2026')"
    )

    cursor.execute("DELETE FROM ferry_rates")
    ferry_routes = [
        ("Helsinki - Travemünde", 1050, "2026-01-01", None),
        ("Hanko - Lübeck",        1010, "2026-01-01", None),
        ("Hanko - Rostock",        750, "2026-01-01", None),
        ("Kotka - Antwerpen",     1800, "2026-01-01", None),
    ]
    cursor.executemany(
        "INSERT INTO ferry_rates (route, price, valid_from, valid_to) VALUES (?,?,?,?)",
        ferry_routes,
    )

    conn.commit()
    conn.close()
    print("migrate_hallinta.py valmis.")
    print(f"  {len(maintenance_rows)} huoltomerkintää")
    print("  1 km_rate-rivi")
    print(f"  {len(ferry_routes)} ferry_rate-rivi")


if __name__ == "__main__":
    from db_config import get_db_path
    run_migration(get_db_path())

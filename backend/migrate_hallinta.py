import sqlite3
from datetime import date, timedelta

conn = sqlite3.connect("freight.db")
cursor = conn.cursor()

# --- 1. ALTER TABLE trailers ---
existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(trailers)").fetchall()}
new_trailer_cols = [
    ("inspection_date",                    "TEXT"),
    ("inspection_due",                     "TEXT"),
    ("refrigeration_service_date",         "TEXT"),
    ("refrigeration_service_due",          "TEXT"),
    ("refrigeration_service_interval_months", "INTEGER DEFAULT 6"),
    ("maintenance_notes",                  "TEXT"),
]
for col, typedef in new_trailer_cols:
    if col not in existing_cols:
        cursor.execute(f"ALTER TABLE trailers ADD COLUMN {col} {typedef}")
        print(f"  + trailers.{col} lisätty")

# --- 2. CREATE TABLE trailer_maintenance ---
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

# --- 3. CREATE TABLE km_rates ---
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

# --- 4. CREATE TABLE ferry_rates ---
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

# --- Demo-data: trailer_maintenance ---
# Haetaan trailereiden plate_number-arvot
trailers = cursor.execute("SELECT plate_number, trailer_type FROM trailers").fetchall()
trailer_map = {t[0]: t[1] for t in trailers}

cursor.execute("DELETE FROM trailer_maintenance")

today = date.today()
maintenance_rows = []

# Inspections
for plate, days_ago, next_days in [
    ("URV-001", 365, 365),
    ("URV-002", 180, 545),
    ("SRV-001", 270, 460),
    ("CRT-001", 90, 640),
    ("HRV-001", 400, 330),
]:
    maintenance_rows.append((
        plate, "INSPECTION",
        (today - timedelta(days=days_ago)).isoformat(),
        (today + timedelta(days=next_days - days_ago)).isoformat(),
        "Katsastus OK"
    ))

# Refrigeration (vain thermo-tyypit)
for plate, days_ago, next_days in [
    ("URV-001", 120, 180),
    ("URV-002", 30, 150),
    ("TRV-001", 200, -20),  # erääntynyt: next_due menneisyydessä
]:
    ttype = trailer_map.get(plate, "")
    if "Umpikaappi" in ttype:
        maintenance_rows.append((
            plate, "REFRIGERATION",
            (today - timedelta(days=days_ago)).isoformat(),
            (today + timedelta(days=next_days)).isoformat(),
            "Kylmäkonehuolto suoritettu"
        ))

cursor.executemany("""
    INSERT INTO trailer_maintenance (trailer_id, maintenance_type, date, next_due, notes)
    VALUES (?,?,?,?,?)
""", maintenance_rows)

# --- Päivitä trailereiden inspection_due ja refrigeration_service_due ---
# Erääntynyt — menneisyydessä
cursor.execute("UPDATE trailers SET inspection_date='2025-05-01', inspection_due=? WHERE plate_number='HRV-001'",
               ((today - timedelta(days=20)).isoformat(),))
# Pian (<30 pv)
cursor.execute("UPDATE trailers SET inspection_date='2025-11-01', inspection_due=? WHERE plate_number='URV-003'",
               ((today + timedelta(days=18)).isoformat(),))
cursor.execute("UPDATE trailers SET inspection_date='2025-11-15', inspection_due=? WHERE plate_number='CRT-002'",
               ((today + timedelta(days=25)).isoformat(),))
# Normaali (>30 pv)
cursor.execute("UPDATE trailers SET inspection_date='2025-06-01', inspection_due=? WHERE plate_number='URV-001'",
               ((today + timedelta(days=365 - 120)).isoformat(),))
cursor.execute("UPDATE trailers SET inspection_date='2025-12-01', inspection_due=? WHERE plate_number='URV-002'",
               ((today + timedelta(days=180)).isoformat(),))
cursor.execute("UPDATE trailers SET inspection_date='2025-08-01', inspection_due=? WHERE plate_number='SRV-001'",
               ((today + timedelta(days=90)).isoformat(),))
cursor.execute("UPDATE trailers SET inspection_date='2026-01-15', inspection_due=? WHERE plate_number='CRT-001'",
               ((today + timedelta(days=120)).isoformat(),))

# Kylmäkonehuolto (vain thermo-trailerit)
cursor.execute("""UPDATE trailers SET
    refrigeration_service_date='2025-12-01',
    refrigeration_service_due=?,
    refrigeration_service_interval_months=6
WHERE plate_number='URV-001'""", ((today + timedelta(days=60)).isoformat(),))

cursor.execute("""UPDATE trailers SET
    refrigeration_service_date='2026-01-15',
    refrigeration_service_due=?,
    refrigeration_service_interval_months=6
WHERE plate_number='URV-002'""", ((today + timedelta(days=15)).isoformat(),))

cursor.execute("""UPDATE trailers SET
    refrigeration_service_date='2025-10-01',
    refrigeration_service_due=?,
    refrigeration_service_interval_months=6
WHERE plate_number='TRV-001'""", ((today - timedelta(days=20)).isoformat(),))

cursor.execute("""UPDATE trailers SET
    refrigeration_service_date='2026-02-01',
    refrigeration_service_due=?,
    refrigeration_service_interval_months=6
WHERE plate_number='TRV-002'""", ((today + timedelta(days=95)).isoformat(),))

# --- Demo-data: km_rates ---
cursor.execute("DELETE FROM km_rates")
cursor.execute("""
    INSERT INTO km_rates (valid_from, valid_to, domestic_rate, continent_rate, notes)
    VALUES ('2026-01-01', NULL, 1.85, 2.20, 'Perushinnoittelu 2026')
""")

# --- Demo-data: ferry_rates ---
cursor.execute("DELETE FROM ferry_rates")
ferry_routes = [
    ("Helsinki - Travemünde", 1050, "2026-01-01", None),
    ("Hanko - Lübeck",        1010, "2026-01-01", None),
    ("Hanko - Rostock",        750, "2026-01-01", None),
    ("Kotka - Antwerpen",     1800, "2026-01-01", None),
]
cursor.executemany("""
    INSERT INTO ferry_rates (route, price, valid_from, valid_to)
    VALUES (?,?,?,?)
""", ferry_routes)

conn.commit()
conn.close()
print("migrate_hallinta.py valmis.")
print(f"  {len(maintenance_rows)} huoltomerkintää")
print(f"  1 km_rate-rivi")
print(f"  {len(ferry_routes)} ferry_rate-rivi")

import sqlite3

conn = sqlite3.connect("freight.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
)
""")

defaults = [
    ("forwarder_name",        "Demo Freight Oy"),
    ("forwarder_address",     "Logistiikkakatu 1, 00100 Helsinki"),
    ("forwarder_phone",       "+358 9 1234567"),
    ("forwarder_email",       "info@demofreight.fi"),
    ("forwarder_vat",         "FI12345678"),
    ("forwarder_business_id", "1234567-8"),
    ("alert_inspection_days",    "30"),
    ("alert_refrigeration_days", "30"),
    ("alert_load_pct",           "90"),
    ("alert_late_hours",         "2"),
    ("alert_inspection_enabled",    "1"),
    ("alert_refrigeration_enabled", "1"),
    ("alert_load_enabled",          "1"),
    ("alert_late_enabled",          "1"),
]

cursor.executemany("""
    INSERT INTO settings (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO NOTHING
""", defaults)

conn.commit()
conn.close()
print(f"migrate_settings.py valmis — {len(defaults)} asetusta syötetty.")

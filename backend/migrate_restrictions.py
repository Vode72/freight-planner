import sqlite3

conn = sqlite3.connect("freight.db")
cursor = conn.cursor()

# --- country_restrictions ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS country_restrictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT NOT NULL,
    restriction_type TEXT NOT NULL,
    day_of_week TEXT,
    date_from TEXT,
    date_to TEXT,
    time_from TEXT,
    time_to TEXT,
    min_weight_t REAL DEFAULT 3.5,
    description TEXT,
    severity TEXT DEFAULT 'orange',
    exemptions TEXT,
    active INTEGER DEFAULT 1
)
""")

# --- terminals ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS terminals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    country_code TEXT NOT NULL,
    city TEXT NOT NULL,
    address TEXT,
    contact_person TEXT,
    phone TEXT,
    has_tail_lift INTEGER DEFAULT 1,
    notes TEXT,
    active INTEGER DEFAULT 1
)
""")

# --- trips-taulun uudet sarakkeet ---
existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(trips)").fetchall()}
if "tail_lift_unloading" not in existing_cols:
    cursor.execute("ALTER TABLE trips ADD COLUMN tail_lift_unloading INTEGER DEFAULT 0")
if "unloading_terminal_id" not in existing_cols:
    cursor.execute("ALTER TABLE trips ADD COLUMN unloading_terminal_id INTEGER REFERENCES terminals(id)")

# --- Demo-data: country_restrictions ---
cursor.execute("DELETE FROM country_restrictions")

restrictions = [
    # CH
    ("CH", "SUNDAY_BAN",  "sun", None,    None,    "00:00", "24:00", 3.5,  "Sunnuntaikielto — ei poikkeuksia", "red",    "Ei poikkeuksia"),
    ("CH", "NIGHT_BAN",   "all", None,    None,    "22:00", "05:00", 3.5,  "Yöajokielto joka yö",              "red",    None),
    ("CH", "WEIGHT_LIMIT","all", None,    None,    None,    None,    40.0, "Max GVW 40t (EU 44t ei kelpaa)",   "red",    None),
    # DE
    ("DE", "SUNDAY_BAN",  "sun", None,    None,    "00:00", "22:00", 7.5,  "Sunnuntaikielto",                  "orange", None),
    ("DE", "SUMMER_BAN",  "sat", "07-01", "08-31", "00:00", "22:00", 7.5,  "Kesälauantairajoitus heinä-elokuu","yellow", "Tietyt päätiet"),
    # AT
    ("AT", "SUNDAY_BAN",  "sun", None,    None,    "00:00", "22:00", 7.5,  "Sunnuntaikielto",                  "orange", None),
    ("AT", "NIGHT_BAN",   "all", "11-01", "03-31", "22:00", "05:00", 7.5,  "Brenner-reitin yökielto talvikaudella", "orange", None),
    # FR
    ("FR", "SUNDAY_BAN",  "sun", None,    None,    "00:00", "22:00", 7.5,  "Sunnuntaikielto",                  "orange", None),
    # IT
    ("IT", "SUNDAY_BAN",  "sun", None,    None,    "07:00", "22:00", 7.5,  "Sunnuntaikielto",                  "orange", None),
    ("IT", "SUMMER_BAN",  "sat", "06-01", "09-30", "08:00", "16:00", 7.5,  "Kesälauantairajoitus",             "yellow", None),
    ("IT", "WEIGHT_LIMIT","all", None,    None,    None,    None,    44.0, "Max GVW 44t",                      "orange", None),
    # PL
    ("PL", "SUNDAY_BAN",  "sun", None,    None,    "08:00", "22:00", 12.0, "Sunnuntaikielto",                  "orange", None),
    # CZ
    ("CZ", "SUNDAY_BAN",  "sun", None,    None,    "13:00", "22:00", 7.5,  "Sunnuntaikielto",                  "yellow", None),
    # SK
    ("SK", "SUNDAY_BAN",  "sun", None,    None,    "00:00", "22:00", 7.5,  "Sunnuntaikielto",                  "orange", None),
    # LU
    ("LU", "SUNDAY_BAN",  "sun", None,    None,    "00:00", "21:45", 7.5,  "Sunnuntaikielto",                  "orange", None),
]

cursor.executemany("""
    INSERT INTO country_restrictions
        (country_code, restriction_type, day_of_week, date_from, date_to,
         time_from, time_to, min_weight_t, description, severity, exemptions)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)
""", restrictions)

# --- Demo-data: terminals ---
cursor.execute("DELETE FROM terminals")

terminals = [
    ("Demo Terminal Helsinki",   "FI", "Helsinki",   "Vuosaarentie 10, 00980 Helsinki"),
    ("Demo Terminal Tampere",    "FI", "Tampere",    "Naistenlahdenranta 4, 33200 Tampere"),
    ("Demo Terminal Antwerpen",  "BE", "Antwerpen",  "Havenstraat 12, 2030 Antwerpen"),
    ("Demo Terminal Bruxelles",  "BE", "Bruxelles",  "Rue du Port 8, 1000 Bruxelles"),
    ("Demo Terminal Rotterdam",  "NL", "Rotterdam",  "Waalhaven 34, 3087 Rotterdam"),
    ("Demo Terminal Amsterdam",  "NL", "Amsterdam",  "Westpoort 17, 1048 Amsterdam"),
    ("Demo Terminal Hamburg",    "DE", "Hamburg",    "Hafenweg 22, 20457 Hamburg"),
    ("Demo Terminal Frankfurt",  "DE", "Frankfurt",  "Industriestr. 45, 60327 Frankfurt am Main"),
    ("Demo Terminal Paris",      "FR", "Rungis",     "Rue de la Logistique 5, 94150 Rungis"),
    ("Demo Terminal Lyon",       "FR", "Lyon",       "Avenue du Port 18, 69007 Lyon"),
    ("Demo Terminal Zürich",     "CH", "Zürich",     "Industriestrasse 8, 8005 Zürich"),
    ("Demo Terminal Basel",      "CH", "Basel",      "Rheinweg 14, 4058 Basel"),
    ("Demo Terminal Wien",       "AT", "Wien",       "Laxenburger Str. 20, 1100 Wien"),
    ("Demo Terminal Innsbruck",  "AT", "Innsbruck",  "Innsbrucker Str. 3, 6020 Innsbruck"),
    ("Demo Terminal Milano",     "IT", "Milano",     "Via della Logistica 9, 20142 Milano"),
    ("Demo Terminal Roma",       "IT", "Roma",       "Via Portuense 33, 00148 Roma"),
]

cursor.executemany("""
    INSERT INTO terminals (name, country_code, city, address)
    VALUES (?,?,?,?)
""", terminals)

conn.commit()
conn.close()
print("Migraatio valmis: country_restrictions, terminals ja trips-sarakkeet lisätty.")

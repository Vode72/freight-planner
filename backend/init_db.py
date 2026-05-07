import sqlite3

conn = sqlite3.connect("freight.db")
cursor = conn.cursor()

# Poistetaan vanhat taulut
cursor.execute("DROP TABLE IF EXISTS costs")
cursor.execute("DROP TABLE IF EXISTS orders")
cursor.execute("DROP TABLE IF EXISTS trucks")
cursor.execute("DROP TABLE IF EXISTS trips")
cursor.execute("DROP TABLE IF EXISTS trailers")
cursor.execute("DROP TABLE IF EXISTS carriers")

# Trips taulu
cursor.execute("""
CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id TEXT UNIQUE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Suunniteltu',
    first_pickup_country TEXT,
    first_pickup_zip TEXT,
    first_pickup_city TEXT,
    trip_end_country TEXT,
    trip_end_zip TEXT,
    trip_end_city TEXT,
    transport_type TEXT DEFAULT 'Suora',
    carrier_id INTEGER,
    trailer_id INTEGER,
    trailer_type TEXT,
    truck_plate TEXT,
    loading_date TEXT,
    loading_time_start TEXT,
    loading_time_end TEXT,
    delivery_date TEXT,
    delivery_time_start TEXT,
    delivery_time_end TEXT,
    fixed_delivery_date INTEGER DEFAULT 0,
    ferry_route TEXT,
    ferry_departure TEXT,
    ferry_arrival TEXT,
    adr INTEGER DEFAULT 0,
    tail_lift INTEGER DEFAULT 0,
    temperature_controlled INTEGER DEFAULT 0,
    loading_instructions TEXT,
    notes TEXT,
    FOREIGN KEY (carrier_id) REFERENCES carriers(id),
    FOREIGN KEY (trailer_id) REFERENCES trailers(id)
)
""")

# Orders taulu
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE,
    trip_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Vapaa',
    order_reference TEXT,
    pickup_reference TEXT,
    goods_description TEXT,
    incoterms TEXT,
    consignor_name TEXT,
    consignor_address TEXT,
    consignor_country TEXT,
    consignee_name TEXT,
    consignee_address TEXT,
    consignee_country TEXT,
    loading_point_name TEXT,
    loading_point_country TEXT,
    loading_point_zip TEXT,
    loading_point_city TEXT,
    unloading_point_name TEXT,
    unloading_point_country TEXT,
    unloading_point_zip TEXT,
    unloading_point_city TEXT,
    pallet_type TEXT,
    quantity INTEGER DEFAULT 1,
    pallet_width REAL DEFAULT 0,
    pallet_length REAL DEFAULT 0,
    pallet_height REAL DEFAULT 0,
    loading_meters REAL DEFAULT 0,
    volume REAL DEFAULT 0,
    weight REAL DEFAULT 0,
    stackable INTEGER DEFAULT 0,
    adr INTEGER DEFAULT 0,
    tail_lift INTEGER DEFAULT 0,
    insured INTEGER DEFAULT 0,
    high_value INTEGER DEFAULT 0,
    pre_advise INTEGER DEFAULT 0,
    time_slot_loading INTEGER DEFAULT 0,
    time_slot_delivery INTEGER DEFAULT 0,
    min_temperature REAL,
    max_temperature REAL,
    temperature_monitoring INTEGER DEFAULT 0,
    required_compartment TEXT DEFAULT 'koko kärry',
    loading_instructions TEXT,
    loading_date TEXT,
    loading_time_start TEXT,
    loading_time_end TEXT,
    delivery_date TEXT,
    delivery_time_start TEXT,
    delivery_time_end TEXT,
    FOREIGN KEY (trip_id) REFERENCES trips(id)
)
""")

# Costs taulu
cursor.execute("""
CREATE TABLE IF NOT EXISTS costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER NOT NULL,
    cost_code TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL DEFAULT 0,
    cost_type TEXT DEFAULT 'cost',
    custom_description TEXT,
    FOREIGN KEY (trip_id) REFERENCES trips(id)
)
""")

# Trailers taulu
cursor.execute("""
CREATE TABLE IF NOT EXISTS trailers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL,
    identifier TEXT NOT NULL,
    trailer_type TEXT NOT NULL,
    leasing_company TEXT DEFAULT 'TIP Trailer Services',
    leasing_rate REAL DEFAULT 0,
    rental_rate REAL DEFAULT 0,
    status TEXT DEFAULT 'Vapaa'
)
""")

# Carriers taulu
cursor.execute("""
CREATE TABLE IF NOT EXISTS carriers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    business_id TEXT,
    contact_person TEXT,
    phone TEXT
)
""")

# Trucks taulu
cursor.execute("""
CREATE TABLE IF NOT EXISTS trucks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL,
    carrier_id INTEGER NOT NULL,
    status TEXT DEFAULT 'Vapaa',
    FOREIGN KEY (carrier_id) REFERENCES carriers(id)
)
""")

# Lisätään trailerit
trailers = [
    ("URV-001", "FB-2401", "Umpikaappi", 42, 65),
    ("URV-002", "FB-2402", "Umpikaappi", 42, 65),
    ("URV-003", "FB-2403", "Umpikaappi", 42, 65),
    ("SRV-001", "FS-2301", "Sivuaukeava", 45, 70),
    ("SRV-002", "FS-2302", "Sivuaukeava", 45, 70),
    ("TRV-001", "FD-1801", "Umpikaappi 2-koneinen", 43, 67),
    ("TRV-002", "FD-1802", "Umpikaappi 2-koneinen", 43, 67),
    ("CRT-001", "CT-3201", "Pressutrailer", 35, 54),
    ("CRT-002", "CT-3202", "Pressutrailer", 35, 54),
    ("CRT-003", "CT-3203", "Pressutrailer", 35, 54),
    ("HRV-001", "CM-4101", "Megatrailer", 38, 59),
    ("HRV-002", "CM-4102", "Megatrailer", 38, 59),
]

cursor.executemany("""
    INSERT INTO trailers (plate_number, identifier, trailer_type, leasing_rate, rental_rate)
    VALUES (?, ?, ?, ?, ?)
""", trailers)

# Lisätään kuljetusyhtiöt
carriers = [
    ("Nordic Freight Oy", "FI", "Helsinki", "1234567-8", "Matti Virtanen", "+358 40 123 4567"),
    ("Baltic Road Oy", "FI", "Turku", "2345678-9", "Juha Mäkinen", "+358 40 234 5678"),
    ("Pohjan Kuljetus Oy", "FI", "Oulu", "3456789-0", "Pekka Korhonen", "+358 40 345 6789"),
    ("Euro Trans GmbH", "DE", "Hamburg", "DE123456789", "Hans Mueller", "+49 40 123 4567"),
    ("Continental Cargo BV", "NL", "Rotterdam", "NL123456789", "Jan van Berg", "+31 10 123 4567"),
    ("Scan Logistics AB", "SE", "Göteborg", "SE123456789", "Erik Svensson", "+46 31 123 4567"),
]

cursor.executemany("""
    INSERT INTO carriers (name, country, city, business_id, contact_person, phone)
    VALUES (?, ?, ?, ?, ?, ?)
""", carriers)

# Lisätään vetäjät
trucks = [
    ("NRF-001", 1),
    ("NRF-002", 1),
    ("BLR-001", 2),
    ("BLR-002", 2),
    ("PHK-001", 3),
    ("PHK-002", 3),
    ("ETR-001", 4),
    ("ETR-002", 4),
    ("CTC-001", 5),
    ("CTC-002", 5),
    ("SCL-001", 6),
    ("SCL-002", 6),
]

cursor.executemany("""
    INSERT INTO trucks (plate_number, carrier_id)
    VALUES (?, ?)
""", trucks)

conn.commit()
conn.close()
print("Tietokanta alustettu onnistuneesti.")
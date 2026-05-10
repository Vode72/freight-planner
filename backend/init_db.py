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
cursor.execute("DROP TABLE IF EXISTS customers")
cursor.execute("DROP TABLE IF EXISTS fuel_rates")

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

# Customers taulu
cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    business_id TEXT,
    address TEXT,
    zip TEXT,
    city TEXT,
    country TEXT NOT NULL DEFAULT 'FI',
    contact_person TEXT,
    phone TEXT,
    email TEXT,
    customer_type TEXT DEFAULT 'molemmat',
    notes TEXT
)
""")

# Fuel rates taulu
cursor.execute("""
CREATE TABLE IF NOT EXISTS fuel_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    valid_from TEXT NOT NULL,
    valid_to TEXT NOT NULL,
    multiplier REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

fuel_rates_demo = [
    ("2026-01-01", "2026-01-31", 1.15),
    ("2026-02-01", "2026-02-28", 1.16),
    ("2026-03-01", "2026-03-31", 1.18),
    ("2026-04-01", "2026-04-30", 1.17),
    ("2026-05-01", "2026-05-31", 1.19),
]
cursor.executemany("""
    INSERT INTO fuel_rates (valid_from, valid_to, multiplier) VALUES (?, ?, ?)
""", fuel_rates_demo)

# Lisätään asiakkaat
customers = [
    ("Kesko Logistics Oy", "1234567-8", "Satamakatu 5", "00160", "Helsinki", "FI", "Antti Leinonen", "+358 40 111 2222", "antti.leinonen@kesko.fi", "consignee", None),
    ("Rautakesko Oy", "2345678-9", "Kehräämöntie 3", "04200", "Kerava", "FI", "Satu Niemi", "+358 40 222 3333", "satu.niemi@rautakesko.fi", "molemmat", None),
    ("S-ryhmä Logistiikka", "3456789-0", "Fleminginkatu 34", "00510", "Helsinki", "FI", "Ville Hakala", "+358 40 333 4444", "ville.hakala@s-ryhma.fi", "consignee", None),
    ("Cargotec Finland Oy", "4567890-1", "Porkkalankatu 5", "00180", "Helsinki", "FI", "Laura Heikkinen", "+358 40 444 5555", "laura.heikkinen@cargotec.com", "consignor", None),
    ("Wihuri Oy", "5678901-2", "Sörnäistenkatu 6", "00580", "Helsinki", "FI", "Mikko Järvinen", "+358 40 555 6666", "mikko.jarvinen@wihuri.fi", "molemmat", None),
    ("Konecranes Oyj", "6789012-3", "Koneenkatu 8", "05830", "Hyvinkää", "FI", "Erika Lund", "+358 40 666 7777", "erika.lund@konecranes.com", "consignor", None),
    ("Meyer Turku Oy", "7890123-4", "Telakkakatu 1", "20810", "Turku", "FI", "Timo Rantanen", "+358 40 777 8888", "timo.rantanen@meyerturku.fi", "molemmat", None),
    ("UPM-Kymmene Oyj", "8901234-5", "Alvar Aallon katu 1", "00100", "Helsinki", "FI", "Minna Saarinen", "+358 40 888 9999", "minna.saarinen@upm.com", "consignor", None),
]

cursor.executemany("""
    INSERT INTO customers (name, business_id, address, zip, city, country, contact_person, phone, email, customer_type, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", customers)

# === DEMO TRIPS ===
trips_demo = [
    # (trip_id, status, fp_country, fp_zip, fp_city, te_country, te_zip, te_city,
    #  transport_type, carrier_id, trailer_id, trailer_type, truck_plate,
    #  loading_date, loading_time_start, loading_time_end,
    #  delivery_date, delivery_time_start, delivery_time_end,
    #  ferry_route, ferry_departure, ferry_arrival,
    #  adr, tail_lift, temperature_controlled, fixed_delivery_date)
    ("TRP-2026-001", "Suunniteltu",
     "FI", "00160", "Helsinki", "DE", "20537", "Hamburg", "Suora",
     1, 1, "Umpikaappi", "NRF-001",
     "2026-05-14", "07:00", "09:00", "2026-05-16", "08:00", "12:00",
     None, None, None, 0, 0, 0, 0),

    ("TRP-2026-002", "Vahvistettu",
     "FI", "20100", "Turku", "SE", "11120", "Stockholm", "Lautta",
     6, 4, "Sivuaukeava", "SCL-001",
     "2026-05-12", "06:00", "08:00", "2026-05-13", "14:00", "16:00",
     "Turku-Stockholm", "2026-05-12 20:00", "2026-05-13 09:00", 0, 0, 0, 0),

    ("TRP-2026-003", "Käynnissä",
     "FI", "00160", "Helsinki", "NL", "3013", "Rotterdam", "Suora",
     2, 8, "Pressutrailer", "BLR-001",
     "2026-05-08", "07:00", "09:00", "2026-05-12", "10:00", "14:00",
     None, None, None, 0, 0, 0, 0),

    ("TRP-2026-004", "Toimitettu",
     "FI", "90100", "Oulu", "DE", "60329", "Frankfurt", "Suora",
     4, 6, "Umpikaappi 2-koneinen", "ETR-001",
     "2026-05-02", "07:00", "10:00", "2026-05-05", "09:00", "13:00",
     None, None, None, 0, 0, 0, 1),

    ("TRP-2026-005", "Laskutettu",
     "FI", "00160", "Helsinki", "EE", "10111", "Tallinn", "Lautta",
     1, 2, "Umpikaappi", "NRF-002",
     "2026-04-28", "08:00", "10:00", "2026-04-29", "12:00", "15:00",
     "Helsinki-Tallinn", "2026-04-28 20:00", "2026-04-29 07:00", 0, 0, 0, 0),

    ("TRP-2026-006", "Vahvistettu",
     "FI", "33100", "Tampere", "PL", "00-001", "Varsova", "Suora",
     3, 11, "Megatrailer", "PHK-001",
     "2026-05-15", "06:00", "09:00", "2026-05-19", "10:00", "14:00",
     None, None, None, 0, 0, 0, 0),

    ("TRP-2026-007", "Suunniteltu",
     "FI", "02100", "Espoo", "NO", "0150", "Oslo", "Suora",
     2, 5, "Sivuaukeava", "BLR-002",
     "2026-05-20", "07:00", "09:00", "2026-05-22", "10:00", "14:00",
     None, None, None, 0, 0, 0, 0),
]

trip_db_ids = []
for t in trips_demo:
    cursor.execute("""
        INSERT INTO trips (trip_id, status,
            first_pickup_country, first_pickup_zip, first_pickup_city,
            trip_end_country, trip_end_zip, trip_end_city, transport_type,
            carrier_id, trailer_id, trailer_type, truck_plate,
            loading_date, loading_time_start, loading_time_end,
            delivery_date, delivery_time_start, delivery_time_end,
            ferry_route, ferry_departure, ferry_arrival,
            adr, tail_lift, temperature_controlled, fixed_delivery_date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, t)
    trip_db_ids.append(cursor.lastrowid)

# === DEMO ORDERS ===
# status: Tilattu (assigned, not yet moving), Käynnissä, Toimitettu
orders_demo = [
    # Trip 1 — TRP-2026-001 Suunniteltu FI→DE
    ("ORD-2026-001", trip_db_ids[0], "Tilattu", "KNC-2026-1401",
     "Nosturikomponentit", "DAP",
     "Konecranes Oyj", "Koneenkatu 8, 05830 Hyvinkää", "FI",
     "ThyssenKrupp AG", "Kaiser-Wilhelm-Str. 100, 47259 Duisburg", "DE",
     "Konecranes Oyj", "FI", "05830", "Hyvinkää",
     "ThyssenKrupp AG", "DE", "47259", "Duisburg",
     "EUR", 12, 5.4, 42.5, 8200,
     "2026-05-14", "2026-05-16"),

    ("ORD-2026-002", trip_db_ids[0], "Tilattu", "UPM-2026-0514",
     "Paperi", "DAP",
     "UPM-Kymmene Oyj", "Alvar Aallon katu 1, 00100 Helsinki", "FI",
     "Mayr-Melnhof GmbH", "Brahmsplatz 6, 1040 Wien", "DE",
     "UPM-Kymmene Oyj", "FI", "00100", "Helsinki",
     "Mayr-Melnhof GmbH", "DE", "47800", "Krefeld",
     "EUR", 18, 3.8, 28.6, 6400,
     "2026-05-14", "2026-05-16"),

    # Trip 2 — TRP-2026-002 Vahvistettu FI→SE
    ("ORD-2026-003", trip_db_ids[1], "Tilattu", "WHR-2026-0512",
     "Elintarvikkeet", "DAP",
     "Wihuri Oy", "Sörnäistenkatu 6, 00580 Helsinki", "FI",
     "Axfood AB", "Solnavägen 3C, 11927 Stockholm", "SE",
     "Wihuri Oy", "FI", "20810", "Turku",
     "Axfood AB", "SE", "11927", "Stockholm",
     "EUR", 32, 8.0, 62.4, 12000,
     "2026-05-12", "2026-05-13"),

    # Trip 3 — TRP-2026-003 Käynnissä FI→NL
    ("ORD-2026-004", trip_db_ids[2], "Käynnissä", "KSK-2026-0508",
     "Teollisuuskemikaalit", "CPT",
     "Kesko Logistics Oy", "Satamakatu 5, 00160 Helsinki", "FI",
     "Brenntag NV", "Handelstraat 87, 3013 Rotterdam", "NL",
     "Kesko Logistics Oy", "FI", "00160", "Helsinki",
     "Brenntag NV", "NL", "3013", "Rotterdam",
     "EUR", 22, 6.8, 51.2, 9500,
     "2026-05-08", "2026-05-12"),

    ("ORD-2026-005", trip_db_ids[2], "Käynnissä", "RKS-2026-0508",
     "Rakennustarvikkeet", "DAP",
     "Rautakesko Oy", "Kehräämöntie 3, 04200 Kerava", "FI",
     "Bouwmarkt BV", "Industrieweg 45, 2700 Zoetermeer", "NL",
     "Rautakesko Oy", "FI", "04200", "Kerava",
     "Bouwmarkt BV", "NL", "2700", "Zoetermeer",
     "FIN", 16, 5.2, 38.4, 11200,
     "2026-05-08", "2026-05-12"),

    ("ORD-2026-006", trip_db_ids[2], "Käynnissä", "MYR-2026-0508",
     "Laivaosat", "EXW",
     "Meyer Turku Oy", "Telakkakatu 1, 20810 Turku", "FI",
     "Damen Shipyards BV", "Avelingen-West 20, 4200 Gorinchem", "NL",
     "Meyer Turku Oy", "FI", "20810", "Turku",
     "Damen Shipyards BV", "NL", "4200", "Gorinchem",
     "EUR", 10, 3.5, 26.5, 4800,
     "2026-05-08", "2026-05-12"),

    # Trip 4 — TRP-2026-004 Toimitettu FI→DE
    ("ORD-2026-007", trip_db_ids[3], "Toimitettu", "UPM-2026-0502",
     "Paperirullat", "DAP",
     "UPM-Kymmene Oyj", "Alvar Aallon katu 1, 00100 Helsinki", "FI",
     "StoraEnso GmbH", "Darmstädter Landstr. 115, 60314 Frankfurt", "DE",
     "UPM-Kymmene Oyj", "FI", "00100", "Helsinki",
     "StoraEnso GmbH", "DE", "60329", "Frankfurt",
     "EUR", 24, 7.6, 56.8, 14000,
     "2026-05-02", "2026-05-05"),

    ("ORD-2026-008", trip_db_ids[3], "Toimitettu", "KNC-2026-0502",
     "Nosturiosat", "CPT",
     "Konecranes Oyj", "Koneenkatu 8, 05830 Hyvinkää", "FI",
     "Demag Cranes GmbH", "Ruhrstr. 28, 58300 Wetter", "DE",
     "Konecranes Oyj", "FI", "05830", "Hyvinkää",
     "Demag Cranes GmbH", "DE", "58300", "Wetter",
     "EUR", 14, 4.8, 36.0, 7300,
     "2026-05-02", "2026-05-05"),

    # Trip 5 — TRP-2026-005 Laskutettu FI→EE
    ("ORD-2026-009", trip_db_ids[4], "Toimitettu", "SRY-2026-0428",
     "Päivittäistavarat", "DAP",
     "S-ryhmä Logistiikka", "Fleminginkatu 34, 00510 Helsinki", "FI",
     "Prisma Eesti AS", "Peterburi tee 2, 11415 Tallinn", "EE",
     "S-ryhmä Logistiikka", "FI", "00510", "Helsinki",
     "Prisma Eesti AS", "EE", "10111", "Tallinn",
     "EUR", 42, 10.4, 81.6, 16500,
     "2026-04-28", "2026-04-29"),

    # Trip 6 — TRP-2026-006 Vahvistettu FI→PL
    ("ORD-2026-010", trip_db_ids[5], "Tilattu", "WHR-2026-0515",
     "Pakkausmateriaalit", "DAP",
     "Wihuri Oy", "Sörnäistenkatu 6, 00580 Helsinki", "FI",
     "Leroy Merlin Polska", "Al. Jerozolimskie 92, 00-807 Warszawa", "PL",
     "Wihuri Oy", "FI", "00580", "Helsinki",
     "Leroy Merlin Polska", "PL", "00-807", "Varsova",
     "EUR", 18, 6.5, 50.7, 7200,
     "2026-05-15", "2026-05-19"),

    ("ORD-2026-011", trip_db_ids[5], "Tilattu", "CGT-2026-0515",
     "Koneenvaraosat", "CPT",
     "Cargotec Finland Oy", "Porkkalankatu 5, 00180 Helsinki", "FI",
     "Famur SA", "ul. Armii Krajowej 51, 40-698 Katowice", "PL",
     "Cargotec Finland Oy", "FI", "00180", "Helsinki",
     "Famur SA", "PL", "40-698", "Katowice",
     "EUR", 14, 4.2, 31.5, 5800,
     "2026-05-15", "2026-05-19"),

    # Trip 7 — TRP-2026-007 Suunniteltu FI→NO
    ("ORD-2026-012", trip_db_ids[6], "Tilattu", "KSK-2026-0520",
     "Päivittäistavaroita", "DAP",
     "Kesko Logistics Oy", "Satamakatu 5, 00160 Helsinki", "FI",
     "Rema 1000 AS", "Telemarksgata 8, 0579 Oslo", "NO",
     "Kesko Logistics Oy", "FI", "00160", "Helsinki",
     "Rema 1000 AS", "NO", "0150", "Oslo",
     "EUR", 36, 9.2, 71.5, 13800,
     "2026-05-20", "2026-05-22"),
]

cursor.executemany("""
    INSERT INTO orders (order_id, trip_id, status, order_reference,
        goods_description, incoterms,
        consignor_name, consignor_address, consignor_country,
        consignee_name, consignee_address, consignee_country,
        loading_point_name, loading_point_country, loading_point_zip, loading_point_city,
        unloading_point_name, unloading_point_country, unloading_point_zip, unloading_point_city,
        pallet_type, quantity, loading_meters, volume, weight,
        loading_date, delivery_date)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", orders_demo)

# === DEMO COSTS ===
costs_demo = [
    # Trip 3 — Käynnissä FI→NL
    (trip_db_ids[2], "120", "FREIGHT", 2800.0, "revenue", None),
    (trip_db_ids[2], "200", "POLTTOAINELISÄ", 210.0, "cost", None),
    (trip_db_ids[2], "310", "HOLLANTI + SAKSA TIEMAKSU", 95.0, "cost", None),

    # Trip 4 — Toimitettu FI→DE
    (trip_db_ids[3], "120", "FREIGHT", 3200.0, "revenue", None),
    (trip_db_ids[3], "200", "POLTTOAINELISÄ", 280.0, "cost", None),
    (trip_db_ids[3], "300", "SAKSAN TIEMAKSU", 85.0, "cost", None),
    (trip_db_ids[3], "500", "LAUTTAKUSTANNUS", 340.0, "cost", None),
    (trip_db_ids[3], "400", "TRAILERVUOKRA", 129.0, "cost", None),

    # Trip 5 — Laskutettu FI→EE
    (trip_db_ids[4], "100", "SPOT PRICE", 1800.0, "revenue", None),
    (trip_db_ids[4], "200", "POLTTOAINELISÄ", 130.0, "cost", None),
    (trip_db_ids[4], "500", "LAUTTAKUSTANNUS", 180.0, "cost", None),
    (trip_db_ids[4], "400", "TRAILERVUOKRA", 84.0, "cost", None),

    # Trip 6 — Vahvistettu FI→PL (vahvistuksen yhteydessä lisätty)
    (trip_db_ids[5], "120", "FREIGHT", 2400.0, "revenue", None),
    (trip_db_ids[5], "200", "POLTTOAINELISÄ", 195.0, "cost", None),
    (trip_db_ids[5], "400", "TRAILERVUOKRA", 190.0, "cost", None),
]

cursor.executemany("""
    INSERT INTO costs (trip_id, cost_code, description, amount, cost_type, custom_description)
    VALUES (?, ?, ?, ?, ?, ?)
""", costs_demo)

conn.commit()
conn.close()
print("Tietokanta alustettu onnistuneesti.")
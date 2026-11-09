"""baseline: skeema sellaisenaan kuin se oli ennen Alembicia

Jäädytetty kopio skeemasta, jonka init_db.create_schema(), migrate_*.py ja
app.migrate_db() tuottivat (issue #22). Ei muuta dataa:

* tyhjään kantaan luodaan kaikki taulut ja indeksit,
* olemassa olevaan kantaan luodaan vain puuttuvat taulut/indeksit ja
  lisätään sarakkeet, jotka vanhat skriptit lisäsivät ALTER TABLE -lauseilla.

Tätä tiedostoa ei muuteta jälkikäteen — skeemamuutokset tehdään uusina
revisioina.

Revision ID: 0001
Revises:
Create Date: 2026-11-09
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


TABLES = [
    """
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
    loading_started_at TEXT,
    loading_completed_at TEXT,
    delivery_started_at TEXT,
    delivery_completed_at TEXT,
    delivered_at TEXT,
    tail_lift_unloading INTEGER DEFAULT 0,
    unloading_terminal_id INTEGER REFERENCES terminals(id),
    FOREIGN KEY (carrier_id) REFERENCES carriers(id),
    FOREIGN KEY (trailer_id) REFERENCES trailers(id)
)""",
    """
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
)""",
    """
CREATE TABLE IF NOT EXISTS costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER NOT NULL,
    cost_code TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL DEFAULT 0,
    cost_type TEXT DEFAULT 'cost',
    custom_description TEXT,
    FOREIGN KEY (trip_id) REFERENCES trips(id)
)""",
    """
CREATE TABLE IF NOT EXISTS trailers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL,
    identifier TEXT NOT NULL,
    trailer_type TEXT NOT NULL,
    leasing_company TEXT DEFAULT 'Demo Trailer Leasing Oy',
    leasing_rate REAL DEFAULT 0,
    rental_rate REAL DEFAULT 0,
    status TEXT DEFAULT 'Vapaa',
    inspection_date TEXT,
    inspection_due TEXT,
    refrigeration_service_date TEXT,
    refrigeration_service_due TEXT,
    refrigeration_service_interval_months INTEGER DEFAULT 6,
    maintenance_notes TEXT
)""",
    """
CREATE TABLE IF NOT EXISTS carriers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    business_id TEXT,
    contact_person TEXT,
    phone TEXT
)""",
    """
CREATE TABLE IF NOT EXISTS trucks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL,
    carrier_id INTEGER NOT NULL,
    status TEXT DEFAULT 'Vapaa',
    FOREIGN KEY (carrier_id) REFERENCES carriers(id)
)""",
    """
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
)""",
    """
CREATE TABLE IF NOT EXISTS fuel_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    valid_from TEXT NOT NULL,
    valid_to TEXT NOT NULL,
    multiplier REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)""",
    """
CREATE TABLE IF NOT EXISTS services (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    default_cost_type TEXT NOT NULL DEFAULT 'cost'
        CHECK (default_cost_type IN ('cost', 'revenue')),
    active INTEGER NOT NULL DEFAULT 1
)""",
    """
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
)""",
    """
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
)""",
    """
CREATE TABLE IF NOT EXISTS trailer_maintenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trailer_id TEXT NOT NULL REFERENCES trailers(plate_number),
    maintenance_type TEXT NOT NULL,
    date TEXT NOT NULL,
    next_due TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
)""",
    """
CREATE TABLE IF NOT EXISTS km_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    domestic_rate REAL NOT NULL,
    continent_rate REAL NOT NULL,
    notes TEXT
)""",
    """
CREATE TABLE IF NOT EXISTS ferry_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route TEXT NOT NULL,
    price REAL NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    notes TEXT
)""",
    """
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
)""",
    """
CREATE TABLE IF NOT EXISTS surcharge_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_code TEXT NOT NULL,
    cost_type TEXT NOT NULL CHECK (cost_type IN ('revenue', 'cost')),
    trade_type TEXT CHECK (trade_type IN ('EXP', 'IMP', 'CROSS', 'DOM')),
    product_type TEXT CHECK (product_type IN ('FTL', 'LTL')),
    country TEXT,
    operator TEXT,
    rate_type TEXT NOT NULL
        CHECK (rate_type IN ('percent', 'fixed', 'per_100kg', 'per_km')),
    rate REAL NOT NULL CHECK (rate >= 0),
    min_amount REAL,
    max_amount REAL,
    valid_from TEXT NOT NULL,
    valid_to TEXT
)""",
    """
CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
)""",
    """
CREATE TABLE IF NOT EXISTS customer_rate_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    origin_country TEXT NOT NULL,
    origin_zip_prefix TEXT,
    dest_country TEXT NOT NULL,
    dest_zip_prefix TEXT,
    product_type TEXT NOT NULL CHECK (product_type IN ('FTL', 'LTL')),
    freight_price REAL NOT NULL CHECK (freight_price >= 0),
    valid_from TEXT NOT NULL,
    valid_to TEXT
)""",
    """
CREATE TABLE IF NOT EXISTS customer_billing_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    service_code TEXT NOT NULL,
    billed INTEGER NOT NULL DEFAULT 1 CHECK (billed IN (0, 1)),
    rate_type TEXT CHECK (rate_type IN
        ('percent', 'fixed', 'per_100kg', 'per_km', 'pass_through')),
    rate REAL CHECK (rate >= 0),
    valid_from TEXT NOT NULL,
    valid_to TEXT
)""",
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_surcharge_rates_lookup "
    "ON surcharge_rates (service_code, cost_type, valid_from)",
    "CREATE INDEX IF NOT EXISTS idx_customer_rate_cards_lookup "
    "ON customer_rate_cards (customer_id, origin_country, dest_country)",
    "CREATE INDEX IF NOT EXISTS idx_customer_billing_rules_lookup "
    "ON customer_billing_rules (customer_id, service_code)",
]

# Sarakkeet, jotka vanhat skriptit lisäsivät jälkikäteen ALTER TABLE -lauseilla
# (app.migrate_db, migrate_restrictions.py, migrate_hallinta.py).
LATE_COLUMNS = {
    "trips": [
        ("loading_started_at", "TEXT"),
        ("loading_completed_at", "TEXT"),
        ("delivery_started_at", "TEXT"),
        ("delivery_completed_at", "TEXT"),
        ("delivered_at", "TEXT"),
        ("tail_lift_unloading", "INTEGER DEFAULT 0"),
        ("unloading_terminal_id", "INTEGER REFERENCES terminals(id)"),
    ],
    "trailers": [
        ("inspection_date", "TEXT"),
        ("inspection_due", "TEXT"),
        ("refrigeration_service_date", "TEXT"),
        ("refrigeration_service_due", "TEXT"),
        ("refrigeration_service_interval_months", "INTEGER DEFAULT 6"),
        ("maintenance_notes", "TEXT"),
    ],
}

def _columns(bind, table):
    return {row[1] for row in bind.exec_driver_sql(f"PRAGMA table_info({table})")}


def upgrade():
    bind = op.get_bind()
    for table, columns in LATE_COLUMNS.items():
        existing = _columns(bind, table)
        for name, typedef in columns:
            if existing and name not in existing:
                bind.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {typedef}")
    for ddl in TABLES:
        bind.exec_driver_sql(ddl)
    for ddl in INDEXES:
        bind.exec_driver_sql(ddl)


def downgrade():
    raise NotImplementedError(
        "Baselinea ei ajeta alas: se poistaisi koko kannan. "
        "Luo puhdas kanta komennolla python reset_demo.py."
    )

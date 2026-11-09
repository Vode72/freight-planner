"""rahakentät kokonaisluvuiksi: sentit (×100) ja yksikköhinnat/prosentit (×10 000)

REAL-rahasarakkeet korvataan INTEGER-sarakkeilla, joiden nimi kertoo
mittakaavan (*_cents, *_e4). Arvot muunnetaan Pythonissa Decimalin kautta
(Decimal(repr(x)), ROUND_HALF_UP) — ei SQLiten ROUND()-funktiolla, joka
pyöristäisi liukulukuesityksen (2.675 × 100 = 267.49999…).

SQLite ei osaa muuttaa sarakkeen tyyppiä eikä poistaa CHECK-ehdon
sarakkeita, joten taulut luodaan uudelleen (SQLiten ohjeen 12 vaiheen
menettely): uusi taulu → data → vanhan poisto → uudelleennimeäminen →
indeksit. AUTOINCREMENT-laskuri säilytetään.

CHECK (typeof(...) = 'integer') varmistaa, ettei rahasarakkeeseen päädy
enää liukulukua.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-09
"""
from decimal import Decimal, ROUND_HALF_UP

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _int(col, extra=""):
    return f"{col} INTEGER{extra} CHECK ({col} IS NULL OR typeof({col}) = 'integer')"


# Jäädytetty kopio money.MONEY_COLUMNS-määrittelystä:
# taulu → [(vanha sarake, uusi sarake, desimaalit)]
CONVERSIONS = {
    "costs": [("amount", "amount_cents", 2)],
    "trailers": [("leasing_rate", "leasing_rate_cents", 2),
                 ("rental_rate", "rental_rate_cents", 2)],
    "ferry_rates": [("price", "price_cents", 2)],
    "km_rates": [("domestic_rate", "domestic_rate_e4", 4),
                 ("continent_rate", "continent_rate_e4", 4)],
    "surcharge_rates": [("rate", "rate_e4", 4),
                        ("min_amount", "min_amount_cents", 2),
                        ("max_amount", "max_amount_cents", 2)],
    "customer_rate_cards": [("freight_price", "freight_price_cents", 2)],
    "customer_billing_rules": [("rate", "rate_e4", 4)],
}

NEW_DDL = {
    "costs": f"""
CREATE TABLE {{name}} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER NOT NULL,
    cost_code TEXT NOT NULL,
    description TEXT NOT NULL,
    {_int("amount_cents", " DEFAULT 0")},
    cost_type TEXT DEFAULT 'cost',
    custom_description TEXT,
    FOREIGN KEY (trip_id) REFERENCES trips(id)
)""",
    "trailers": f"""
CREATE TABLE {{name}} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL,
    identifier TEXT NOT NULL,
    trailer_type TEXT NOT NULL,
    leasing_company TEXT DEFAULT 'Demo Trailer Leasing Oy',
    {_int("leasing_rate_cents", " DEFAULT 0")},
    {_int("rental_rate_cents", " DEFAULT 0")},
    status TEXT DEFAULT 'Vapaa',
    inspection_date TEXT,
    inspection_due TEXT,
    refrigeration_service_date TEXT,
    refrigeration_service_due TEXT,
    refrigeration_service_interval_months INTEGER DEFAULT 6,
    maintenance_notes TEXT
)""",
    "ferry_rates": f"""
CREATE TABLE {{name}} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route TEXT NOT NULL,
    {_int("price_cents", " NOT NULL")},
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    notes TEXT
)""",
    "km_rates": f"""
CREATE TABLE {{name}} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    {_int("domestic_rate_e4", " NOT NULL")},
    {_int("continent_rate_e4", " NOT NULL")},
    notes TEXT
)""",
    "surcharge_rates": f"""
CREATE TABLE {{name}} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_code TEXT NOT NULL,
    cost_type TEXT NOT NULL CHECK (cost_type IN ('revenue', 'cost')),
    trade_type TEXT CHECK (trade_type IN ('EXP', 'IMP', 'CROSS', 'DOM')),
    product_type TEXT CHECK (product_type IN ('FTL', 'LTL')),
    country TEXT,
    operator TEXT,
    rate_type TEXT NOT NULL
        CHECK (rate_type IN ('percent', 'fixed', 'per_100kg', 'per_km')),
    {_int("rate_e4", " NOT NULL")},
    {_int("min_amount_cents")},
    {_int("max_amount_cents")},
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    CHECK (rate_e4 >= 0)
)""",
    "customer_rate_cards": f"""
CREATE TABLE {{name}} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    origin_country TEXT NOT NULL,
    origin_zip_prefix TEXT,
    dest_country TEXT NOT NULL,
    dest_zip_prefix TEXT,
    product_type TEXT NOT NULL CHECK (product_type IN ('FTL', 'LTL')),
    {_int("freight_price_cents", " NOT NULL")},
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    CHECK (freight_price_cents >= 0)
)""",
    "customer_billing_rules": f"""
CREATE TABLE {{name}} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    service_code TEXT NOT NULL,
    billed INTEGER NOT NULL DEFAULT 1 CHECK (billed IN (0, 1)),
    rate_type TEXT CHECK (rate_type IN
        ('percent', 'fixed', 'per_100kg', 'per_km', 'pass_through')),
    {_int("rate_e4")},
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    CHECK (rate_e4 >= 0)
)""",
}

# Downgradea varten: baselinen (0001) REAL-skeema
OLD_DDL = {
    "costs": """
CREATE TABLE {name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER NOT NULL,
    cost_code TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL DEFAULT 0,
    cost_type TEXT DEFAULT 'cost',
    custom_description TEXT,
    FOREIGN KEY (trip_id) REFERENCES trips(id)
)""",
    "trailers": """
CREATE TABLE {name} (
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
    "ferry_rates": """
CREATE TABLE {name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route TEXT NOT NULL,
    price REAL NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    notes TEXT
)""",
    "km_rates": """
CREATE TABLE {name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    domestic_rate REAL NOT NULL,
    continent_rate REAL NOT NULL,
    notes TEXT
)""",
    "surcharge_rates": """
CREATE TABLE {name} (
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
    "customer_rate_cards": """
CREATE TABLE {name} (
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
    "customer_billing_rules": """
CREATE TABLE {name} (
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
}

INDEXES = {
    "surcharge_rates": "CREATE INDEX IF NOT EXISTS idx_surcharge_rates_lookup "
                       "ON surcharge_rates (service_code, cost_type, valid_from)",
    "customer_rate_cards": "CREATE INDEX IF NOT EXISTS idx_customer_rate_cards_lookup "
                           "ON customer_rate_cards (customer_id, origin_country, dest_country)",
    "customer_billing_rules": "CREATE INDEX IF NOT EXISTS idx_customer_billing_rules_lookup "
                              "ON customer_billing_rules (customer_id, service_code)",
}


def _to_minor(value, places, where):
    """REAL/teksti → kokonaisluku. Virheellinen arvo keskeyttää migraation."""
    if value is None:
        return None
    try:
        if isinstance(value, float):
            dec = Decimal(repr(value))
        else:
            dec = Decimal(str(value).strip().replace(",", "."))
        if not dec.is_finite():
            raise ValueError
    except Exception:
        raise ValueError(f"{where}: rahasarakkeen arvo ei ole numero: {value!r}") from None
    return int(dec.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP).scaleb(places))


def _from_minor(value, places, where):
    """Kokonaisluku → REAL (vain downgrade: tallennus vanhaan skeemaan)."""
    if value is None:
        return None
    return float(Decimal(int(value)).scaleb(-places))


def _rebuild(bind, table, ddl, mapping, convert):
    """Luo taulun uudelleen. mapping: [(lähdesarake, kohdesarake, desimaalit)]."""
    exists = bind.exec_driver_sql(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not exists:
        return
    tmp = f"{table}__new"
    bind.exec_driver_sql(f"DROP TABLE IF EXISTS {tmp}")
    bind.exec_driver_sql(ddl.format(name=tmp))

    old_cols = [r[1] for r in bind.exec_driver_sql(f"PRAGMA table_info({table})")]
    new_cols = [r[1] for r in bind.exec_driver_sql(f"PRAGMA table_info({tmp})")]
    renamed = {src: (dst, places) for src, dst, places in mapping}
    pairs = []  # (lähdesarake, kohdesarake, desimaalit tai None)
    for col in old_cols:
        if col in renamed:
            dst, places = renamed[col]
            if dst in new_cols:
                pairs.append((col, dst, places))
        elif col in new_cols:
            pairs.append((col, col, None))

    rows = bind.exec_driver_sql(
        f"SELECT {', '.join(src for src, _, _ in pairs)} FROM {table}"
    ).fetchall()
    id_pos = next((i for i, (src, _, _) in enumerate(pairs) if src == "id"), None)
    insert = (f"INSERT INTO {tmp} ({', '.join(dst for _, dst, _ in pairs)}) "
              f"VALUES ({', '.join('?' * len(pairs))})")
    for row in rows:
        values = []
        for i, (src, _, places) in enumerate(pairs):
            value = row[i]
            if places is not None:
                where = f"{table}.{src} (id={row[id_pos] if id_pos is not None else '?'})"
                value = convert(value, places, where)
            values.append(value)
        bind.exec_driver_sql(insert, tuple(values))

    seq = bind.exec_driver_sql(
        "SELECT seq FROM sqlite_sequence WHERE name = ?", (table,)
    ).fetchone()
    bind.exec_driver_sql(f"DROP TABLE {table}")
    bind.exec_driver_sql(f"ALTER TABLE {tmp} RENAME TO {table}")
    if seq is not None:
        bind.exec_driver_sql(
            "UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = ?", (seq[0], table)
        )
        if not bind.exec_driver_sql(
            "SELECT 1 FROM sqlite_sequence WHERE name = ?", (table,)
        ).fetchone():
            bind.exec_driver_sql(
                "INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table, seq[0])
            )
    if table in INDEXES:
        bind.exec_driver_sql(INDEXES[table])


def upgrade():
    bind = op.get_bind()
    for table, mapping in CONVERSIONS.items():
        _rebuild(bind, table, NEW_DDL[table], mapping, _to_minor)


def downgrade():
    bind = op.get_bind()
    for table, mapping in CONVERSIONS.items():
        reverse = [(dst, src, places) for src, dst, places in mapping]
        _rebuild(bind, table, OLD_DDL[table], reverse, _from_minor)

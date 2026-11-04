"""Asiakashinnoittelu: hinnasto (customer_rate_cards) ja lisäsäännöt
(customer_billing_rules).

Määrittely: docs/pricing-engine-spec.md, luvut 8.1, 8.2, 13 ja 14.

Hinnasto: asiakkaan sovittu rahtihinta (120) reitille ja kuljetustyypille.
Reitin kumpikin pää on maa + valinnainen postinumeroalue (postinumeron alku).
Haussa postinumeroalueosuma voittaa pelkän maan, ja pidempi alue lyhyemmän.

Lisäsäännöt: laskutetaanko lisä asiakkaalta (billed) ja valinnainen oma hinta.
Ilman omaa hintaa käytetään listahintaa (surcharge_rates, luku 7). Jos
asiakkaalla ei ole sääntöä lisälle, get_billing_rule palauttaa None.

Kaikki asiakkaat, reitit ja hinnat ovat keksittyä demodataa.
"""

import re

from surcharges import (
    PRODUCT_TYPES, RATE_TYPES as SURCHARGE_RATE_TYPES,
    _norm, _norm_upper, _to_date, _opt_number, _table_exists,
)

# Lisäsäännöissä sallitaan myös läpilaskutus (luku 7.1 / 8.2)
BILLING_RATE_TYPES = SURCHARGE_RATE_TYPES + ("pass_through",)

RATE_CARD_COLUMNS = (
    "customer_id", "origin_country", "origin_zip_prefix",
    "dest_country", "dest_zip_prefix", "product_type", "freight_price",
    "valid_from", "valid_to",
)

BILLING_RULE_COLUMNS = (
    "customer_id", "service_code", "billed", "rate_type", "rate",
    "valid_from", "valid_to",
)

_ZIP_PREFIX_RE = re.compile(r"^[A-Z0-9]+$")
_TRUE_VALUES = {"1", "true", "yes", "kyllä", "on"}
_FALSE_VALUES = {"0", "false", "no", "ei", "off"}


# ── Skeema ────────────────────────────────────────────────────────────

def ensure_customer_pricing_tables(conn):
    """Luo customer_rate_cards- ja customer_billing_rules-taulut. Idempotentti."""
    conn.execute("""
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
)
""")
    conn.execute("""
CREATE INDEX IF NOT EXISTS idx_customer_rate_cards_lookup
    ON customer_rate_cards (customer_id, origin_country, dest_country)
""")
    conn.execute("""
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
)
""")
    conn.execute("""
CREATE INDEX IF NOT EXISTS idx_customer_billing_rules_lookup
    ON customer_billing_rules (customer_id, service_code)
""")


# ── Demodata ──────────────────────────────────────────────────────────

# (name, business_id, address, zip, city, country, contact_person, phone,
#  email, customer_type, notes) — keksittyjä
DEMO_PRICING_CUSTOMERS = [
    ("Nordic Demo Plastics Oy", "9990001-1", "Demokatu 1", "33100", "Tampere",
     "FI", "Demo Yhteyshenkilö", "+358 40 000 0001",
     "orders@plastics.example.com", "consignor", "Demoasiakas (hinnasto)"),
    ("Baltic Demo Trading Oy", "9990002-2", "Esimerkkitie 2", "00510",
     "Helsinki", "FI", "Demo Ostaja", "+358 40 000 0002",
     "logistics@trading.example.com", "molemmat", "Demoasiakas (hinnasto)"),
]

# Asiakkaan nimi → hinnastorivit (origin_country, origin_zip_prefix,
# dest_country, dest_zip_prefix, product_type, freight_price, valid_from, valid_to)
DEMO_RATE_CARDS = {
    "Nordic Demo Plastics Oy": [
        # Luvun 17 esimerkkilaskelma: FI → BE FTL 2 000 €
        ("FI", None, "BE", None, "FTL", 2000, "2026-01-01", None),
        ("FI", None, "DE", None, "FTL", 1850, "2026-01-01", None),
        ("FI", None, "BE", None, "LTL", 650, "2026-01-01", None),
    ],
    "Baltic Demo Trading Oy": [
        # Koko maa ja tarkempi postinumeroalue samalle reitille
        ("FI", None, "EE", None, "FTL", 900, "2026-01-01", None),
        ("FI", "33", "EE", None, "FTL", 980, "2026-01-01", None),
        ("FI", None, "LV", "10", "FTL", 1250, "2026-01-01", None),
        # Hinta vaihtui vuodenvaihteessa
        ("FI", None, "LT", None, "FTL", 1400, "2025-01-01", "2025-12-31"),
        ("FI", None, "LT", None, "FTL", 1450, "2026-01-01", None),
    ],
}

# Asiakkaan nimi → lisäsäännöt (service_code, billed, rate_type, rate,
# valid_from, valid_to)
DEMO_BILLING_RULES = {
    # Luku 17: polttoainelisä sopimuksella 25 %, muut lisät listahinnalla
    "Nordic Demo Plastics Oy": [
        ("200", 1, "percent", 25, "2026-01-01", None),
    ],
    # Luku 8.2: polttoaine sopimuksella, ETS listahinnalla, liikkuvuuspakettia
    # ei laskuteta, satamamaksu läpilaskutetaan 5 % katteella
    "Baltic Demo Trading Oy": [
        ("200", 1, "percent", 22, "2026-01-01", None),
        ("230", 0, None, None, "2026-01-01", None),
        ("510", 1, "pass_through", 5, "2026-01-01", None),
    ],
}


def ensure_demo_customer(conn, customer):
    """Palauttaa demoasiakkaan id:n; luo asiakkaan vain, jos nimeä ei ole."""
    row = conn.execute(
        "SELECT id FROM customers WHERE name = ? ORDER BY id LIMIT 1",
        (customer[0],),
    ).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO customers (name, business_id, address, zip, city, country, "
        "contact_person, phone, email, customer_type, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        customer,
    )
    return cur.lastrowid


def seed_customer_pricing(conn):
    """Lisää demohinnaston ja -säännöt, jos molemmat taulut ovat tyhjiä.

    Palauttaa (hinnastorivit, sääntörivit).
    """
    if not _table_exists(conn, "customers"):
        return 0, 0
    cards = conn.execute("SELECT COUNT(*) FROM customer_rate_cards").fetchone()[0]
    rules = conn.execute("SELECT COUNT(*) FROM customer_billing_rules").fetchone()[0]
    if cards or rules:
        return 0, 0
    added_cards = added_rules = 0
    for customer in DEMO_PRICING_CUSTOMERS:
        name = customer[0]
        cid = ensure_demo_customer(conn, customer)
        for card in DEMO_RATE_CARDS.get(name, []):
            conn.execute(
                f"INSERT INTO customer_rate_cards ({', '.join(RATE_CARD_COLUMNS)}) "
                f"VALUES ({', '.join('?' * len(RATE_CARD_COLUMNS))})",
                (cid, *card),
            )
            added_cards += 1
        for rule in DEMO_BILLING_RULES.get(name, []):
            conn.execute(
                f"INSERT INTO customer_billing_rules ({', '.join(BILLING_RULE_COLUMNS)}) "
                f"VALUES ({', '.join('?' * len(BILLING_RULE_COLUMNS))})",
                (cid, *rule),
            )
            added_rules += 1
    return added_cards, added_rules


def run_customer_pricing_migration(conn):
    """Taulut + demodata tyhjiin tauluihin."""
    ensure_customer_pricing_tables(conn)
    return seed_customer_pricing(conn)


# ── Apufunktiot ───────────────────────────────────────────────────────

def normalize_zip(value, country=None):
    """Postinumero/-alue vertailumuotoon: isot kirjaimet, ei välejä/viivoja.

    Jos maa annetaan, postinumeron alussa oleva maakoodi poistetaan
    (esim. LV-1050 → 1050), jotta "LV-1050" ja "1050" vastaavat toisiaan.
    """
    value = _norm(value)
    if value is None:
        return None
    value = re.sub(r"[\s\-]", "", value).upper()
    country = _norm_upper(country)
    if country and value.startswith(country) and value[len(country):][:1].isdigit():
        value = value[len(country):]
    return value or None


def _as_place(value, label):
    """Reitin pää: {"country", "zip"} tai pelkkä maakoodi merkkijonona."""
    if isinstance(value, dict):
        country, zip_code = value.get("country"), value.get("zip")
    else:
        country, zip_code = value, None
    country = _norm_upper(country)
    if not country:
        raise ValueError(f"{label}: maa puuttuu")
    return country, normalize_zip(zip_code, country)


def _zip_match_len(prefix, zip_code, country):
    """None = ei sovi; 0 = pelkkä maa; n = postinumeroalueen pituus."""
    prefix = normalize_zip(prefix, country)
    if prefix is None:
        return 0
    if zip_code and zip_code.startswith(prefix):
        return len(prefix)
    return None


def _valid_on(row, day):
    if _to_date(row["valid_from"]) > day:
        return False
    return not row["valid_to"] or _to_date(row["valid_to"]) >= day


# ── Haku ──────────────────────────────────────────────────────────────

def find_rate_card(conn, customer_id, origin, dest, product_type, date):
    """Hakee asiakkaan voimassa olevan rahtihinnan reitille (luku 8.1).

    origin/dest: {"country": "FI", "zip": "33100"} tai pelkkä maakoodi.
    Järjestys: postinumeroalueosuma ennen pelkkää maata (ensin osumien määrä,
    sitten alueiden yhteispituus), tasatilanteessa uusin valid_from ja suurin id.
    Palauttaa hinnastorivin (dict) tai None. Puuttuva lähtötieto → ValueError.
    """
    if customer_id in (None, ""):
        raise ValueError("customer_id puuttuu")
    o_country, o_zip = _as_place(origin, "origin")
    d_country, d_zip = _as_place(dest, "dest")
    product = _norm_upper(product_type)
    if product not in PRODUCT_TYPES:
        raise ValueError("product_type on pakollinen (FTL/LTL)")
    day = _to_date(date)

    rows = conn.execute(
        "SELECT * FROM customer_rate_cards WHERE customer_id = ? "
        "AND origin_country = ? AND dest_country = ? AND product_type = ?",
        (customer_id, o_country, d_country, product),
    ).fetchall()

    best, best_key = None, None
    for row in rows:
        row = dict(row)
        if not _valid_on(row, day):
            continue
        o_len = _zip_match_len(row["origin_zip_prefix"], o_zip, o_country)
        d_len = _zip_match_len(row["dest_zip_prefix"], d_zip, d_country)
        if o_len is None or d_len is None:
            continue
        key = (
            (o_len > 0) + (d_len > 0),
            o_len + d_len,
            str(row["valid_from"]),
            row["id"],
        )
        if best_key is None or key > best_key:
            best, best_key = row, key
    return best


def billing_rule_as_dict(row):
    row = dict(row)
    row["billed"] = bool(row["billed"])
    return row


def get_billing_rule(conn, customer_id, service_code, date):
    """Asiakkaan voimassa oleva lisäsääntö palvelukoodille (luku 8.2).

    Palauttaa {id, customer_id, service_code, billed (bool), rate_type, rate,
    valid_from, valid_to} tai None, jos asiakkaalla ei ole sääntöä
    (→ käytetään listahintaa). rate_type None = listahinta, billed False =
    lisää ei laskuteta.
    """
    if customer_id in (None, ""):
        raise ValueError("customer_id puuttuu")
    code = _norm(service_code)
    if not code:
        raise ValueError("service_code puuttuu")
    day = _to_date(date)
    rows = conn.execute(
        "SELECT * FROM customer_billing_rules WHERE customer_id = ? AND service_code = ?",
        (customer_id, code),
    ).fetchall()
    valid = [dict(r) for r in rows if _valid_on(dict(r), day)]
    if not valid:
        return None
    best = max(valid, key=lambda r: (str(r["valid_from"]), r["id"]))
    return billing_rule_as_dict(best)


# ── Syötteen validointi (API) ─────────────────────────────────────────

def _validate_validity(data, clean, errors):
    valid_from = valid_to = None
    try:
        valid_from = _to_date(data.get("valid_from"))
    except ValueError as e:
        errors.append(f"valid_from: {e}")
    if _norm(data.get("valid_to")):
        try:
            valid_to = _to_date(data.get("valid_to"))
        except ValueError as e:
            errors.append(f"valid_to: {e}")
    if valid_from and valid_to and valid_to < valid_from:
        errors.append("valid_to ei voi olla ennen valid_from-päivää")
    clean["valid_from"] = valid_from.isoformat() if valid_from else None
    clean["valid_to"] = valid_to.isoformat() if valid_to else None


def _zip_prefix(data, field, country, errors):
    value = normalize_zip(data.get(field), country)
    if value is not None and not _ZIP_PREFIX_RE.match(value):
        errors.append(f"{field} ei kelpaa: {value}")
    return value


def validate_rate_card_payload(data):
    """Tarkistaa hinnastorivin (ilman customer_id:tä). Palauttaa (clean, errors)."""
    if not isinstance(data, dict):
        return None, ["Virheellinen pyyntö"]
    errors = []
    clean = {}
    for side in ("origin", "dest"):
        country = _norm_upper(data.get(f"{side}_country"))
        if not country:
            errors.append(f"{side}_country puuttuu")
        clean[f"{side}_country"] = country
        clean[f"{side}_zip_prefix"] = _zip_prefix(
            data, f"{side}_zip_prefix", country, errors)

    product = _norm_upper(data.get("product_type"))
    if product not in PRODUCT_TYPES:
        errors.append("product_type on pakollinen (FTL/LTL)")
    clean["product_type"] = product

    price = _opt_number(data, "freight_price", errors)
    if price is None and "freight_price ei ole numero" not in errors:
        errors.append("freight_price puuttuu")
    elif price is not None and price < 0:
        errors.append("freight_price ei voi olla negatiivinen")
    clean["freight_price"] = price

    _validate_validity(data, clean, errors)
    return clean, errors


def _parse_bool(value, errors):
    if value is None or value == "":
        return True  # oletus: lisä laskutetaan
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    text = str(value).strip().lower()
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    errors.append(f"billed ei kelpaa: {value}")
    return None


def validate_billing_rule_payload(data, conn):
    """Tarkistaa lisäsäännön (ilman customer_id:tä). Palauttaa (clean, errors)."""
    if not isinstance(data, dict):
        return None, ["Virheellinen pyyntö"]
    errors = []
    clean = {}

    code = _norm(data.get("service_code"))
    if not code:
        errors.append("service_code puuttuu")
    elif not conn.execute(
        "SELECT 1 FROM services WHERE code = ?", (code,)
    ).fetchone():
        errors.append(f"Tuntematon palvelukoodi: {code}")
    clean["service_code"] = code

    billed = _parse_bool(data.get("billed"), errors)
    clean["billed"] = None if billed is None else int(billed)

    rate_type = _norm(data.get("rate_type"))
    if rate_type is not None and rate_type not in BILLING_RATE_TYPES:
        errors.append(f"rate_type ei kelpaa: {rate_type}")
    clean["rate_type"] = rate_type

    rate = _opt_number(data, "rate", errors)
    if rate is not None and rate < 0:
        errors.append("rate ei voi olla negatiivinen")
    clean["rate"] = rate

    if billed is False and (rate_type is not None or rate is not None):
        errors.append("Omaa hintaa ei voi antaa, jos lisää ei laskuteta")
    elif rate_type is None and rate is not None:
        errors.append("rate vaatii rate_typen")
    elif (rate_type in SURCHARGE_RATE_TYPES and rate is None
          and "rate ei ole numero" not in errors):
        errors.append(f"rate puuttuu — pakollinen rate_typelle {rate_type}")

    _validate_validity(data, clean, errors)
    return clean, errors


def _validity_overlap_sql():
    return ("AND (valid_to IS NULL OR valid_to >= ?) "
            "AND (? IS NULL OR valid_from <= ?)")


def find_rate_card_overlap(conn, customer_id, clean, exclude_id=None):
    """Sama asiakas, reitti (alueineen) ja tuote + päällekkäinen voimassaolo."""
    sql = (
        "SELECT * FROM customer_rate_cards WHERE customer_id = ? "
        "AND origin_country = ? AND origin_zip_prefix IS ? "
        "AND dest_country = ? AND dest_zip_prefix IS ? AND product_type = ? "
        + _validity_overlap_sql()
    )
    params = [
        customer_id, clean["origin_country"], clean["origin_zip_prefix"],
        clean["dest_country"], clean["dest_zip_prefix"], clean["product_type"],
        clean["valid_from"], clean["valid_to"], clean["valid_to"],
    ]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def find_billing_rule_overlap(conn, customer_id, clean, exclude_id=None):
    """Sama asiakas ja palvelukoodi + päällekkäinen voimassaolo."""
    sql = (
        "SELECT * FROM customer_billing_rules WHERE customer_id = ? "
        "AND service_code = ? " + _validity_overlap_sql()
    )
    params = [
        customer_id, clean["service_code"],
        clean["valid_from"], clean["valid_to"], clean["valid_to"],
    ]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def delete_customer_pricing(conn, customer_id):
    """Poistaa asiakkaan hinnaston ja lisäsäännöt (asiakkaan poisto)."""
    conn.execute("DELETE FROM customer_rate_cards WHERE customer_id = ?", (customer_id,))
    conn.execute("DELETE FROM customer_billing_rules WHERE customer_id = ?", (customer_id,))

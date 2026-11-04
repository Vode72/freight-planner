"""Lisähinnat (surcharge_rates) ja lisien laskenta.

Määrittely: docs/pricing-engine-spec.md, luku 7.

Jokainen rivi kohdistuu palvelukoodiin ja suuntaan (cost_type). Sama lisä voi
olla asiakkaalle eri hintainen kuin operaattorin veloitus (esim. ETS: myynti
150 €, kulu 180 €), joten cost_type on pakollinen ja osa kohdistusta.

Kohdistuskentät trade_type, product_type, country ja operator: tyhjä (NULL)
tarkoittaa "kaikki". Tarkin osuma voittaa (luku 7.3).

Kaikki hinnat ja operaattorit ovat keksittyä demodataa.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

RATE_TYPES = ("percent", "fixed", "per_100kg", "per_km")
TRADE_TYPES = ("EXP", "IMP", "CROSS", "DOM")
PRODUCT_TYPES = ("FTL", "LTL")
COST_TYPES = ("revenue", "cost")
HOME_COUNTRY = "FI"

# Tarkkuuspisteet (luku 7.3): maa > tuote > operaattori > suunta.
# Esim. suunta+tuote+maa (8+4+1=13) > suunta+maa (9) > suunta+tuote (5) > suunta (1)
SPECIFICITY_WEIGHTS = {"country": 8, "product_type": 4, "operator": 2, "trade_type": 1}

# Kontekstin kenttä, jota kukin rate_type tarvitsee laskennan pohjaksi
RATE_TYPE_BASE = {
    "percent": "freight_amount",
    "fixed": None,
    "per_100kg": "chargeable_weight",
    "per_km": "km",
}

_TWO_PLACES = Decimal("0.01")

# Demodata — (service_code, cost_type, trade_type, product_type, country,
#             operator, rate_type, rate, min_amount, max_amount, valid_from, valid_to)
_MOBILITY_COUNTRIES = {"BE": 9, "NL": 9, "DE": 8, "FR": 10, "PL": 7}

DEMO_SURCHARGE_RATES = [
    # 230 Liikkuvuuspaketti — myynti, maakohtainen, EXP + IMP
    *[
        ("230", "revenue", tt, None, country, None, "percent", pct,
         None, None, "2026-01-01", None)
        for tt in ("EXP", "IMP")
        for country, pct in _MOBILITY_COUNTRIES.items()
    ],
    # 530 ETS — myynti yleinen (hinta noussut vuodenvaihteessa), kulu operaattorilta
    ("530", "revenue", None, None, None, None, "fixed", 120,
     None, None, "2025-01-01", "2025-12-31"),
    ("530", "revenue", None, None, None, None, "fixed", 150,
     None, None, "2026-01-01", None),
    ("530", "cost", None, None, None, "Demo Ferries", "fixed", 180,
     None, None, "2026-01-01", None),
    # 520 BAF — kulu operaattorilta
    ("520", "cost", None, "FTL", None, "Demo Ferries", "fixed", 300,
     None, None, "2026-01-01", None),
    ("520", "cost", None, "LTL", None, "Demo Ferries", "per_100kg", 0.60,
     15, None, "2026-01-01", None),
    # 540 MARPOL — myynti
    ("540", "revenue", None, "FTL", None, None, "fixed", 45,
     None, None, "2026-01-01", None),
    ("540", "revenue", None, "LTL", None, None, "per_100kg", 0.40,
     5, None, "2026-01-01", None),
]

SURCHARGE_COLUMNS = (
    "service_code", "cost_type", "trade_type", "product_type", "country",
    "operator", "rate_type", "rate", "min_amount", "max_amount",
    "valid_from", "valid_to",
)


# ── Skeema ja demodata ────────────────────────────────────────────────

def ensure_surcharge_rates(conn):
    """Luo surcharge_rates-taulun. Idempotentti."""
    conn.execute("""
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
)
""")
    conn.execute("""
CREATE INDEX IF NOT EXISTS idx_surcharge_rates_lookup
    ON surcharge_rates (service_code, cost_type, valid_from)
""")


def seed_surcharge_rates(conn):
    """Lisää demodatan, jos taulu on tyhjä. Palauttaa lisättyjen rivien määrän."""
    count = conn.execute("SELECT COUNT(*) FROM surcharge_rates").fetchone()[0]
    if count:
        return 0
    conn.executemany(
        f"INSERT INTO surcharge_rates ({', '.join(SURCHARGE_COLUMNS)}) "
        f"VALUES ({', '.join('?' * len(SURCHARGE_COLUMNS))})",
        DEMO_SURCHARGE_RATES,
    )
    return len(DEMO_SURCHARGE_RATES)


def run_surcharges_migration(conn):
    """Taulu + demodata tyhjään tauluun + polttoainelisän siirto (luku 7.5)."""
    ensure_surcharge_rates(conn)
    seeded = seed_surcharge_rates(conn)
    migrate_fuel_rates(conn)
    return seeded


# ── Polttoainelisä (luku 7.5) ─────────────────────────────────────────
#
# Polttoainelisä on palvelu 200, myynti, prosentti rahdista, kaikille
# kohdistuksille yhteinen (kohdistuskentät tyhjiä). Vanha fuel_rates-taulu
# on vain siirron lähde; siirron jälkeen surcharge_rates on ainoa
# tietolähde. /api/fuel-rates muuntaa kerroin ↔ prosentti.

FUEL_SERVICE_CODE = "200"
FUEL_COST_TYPE = "revenue"
FUEL_RATE_TYPE = "percent"
FUEL_MIGRATION_NAME = "fuel_rates_to_surcharge_rates"

# WHERE-ehto, joka rajaa surcharge_rates-taulusta polttoainelisän rivit
FUEL_ROW_FILTER = (
    "service_code = '200' AND cost_type = 'revenue' AND rate_type = 'percent' "
    "AND trade_type IS NULL AND product_type IS NULL "
    "AND country IS NULL AND operator IS NULL"
)


def multiplier_to_rate(multiplier):
    """Kerroin → prosentti: (m − 1) × 100, neljä desimaalia."""
    return round((float(multiplier) - 1.0) * 100, 4)


def rate_to_multiplier(rate):
    """Prosentti → kerroin: 1 + rate / 100.

    Kuusi desimaalia, koska prosentissa on neljä (12.345 % ↔ 1.12345).
    """
    return round(1.0 + float(rate) / 100, 6)


def fuel_row_as_legacy(row):
    """surcharge_rates-rivi vanhan /api/fuel-rates-vastauksen muotoon."""
    row = dict(row)
    return {
        "id": row["id"],
        "valid_from": row["valid_from"],
        "valid_to": row["valid_to"],
        "multiplier": rate_to_multiplier(row["rate"]),
        "created_at": None,
    }


def _ensure_migration_log(conn):
    conn.execute("""
CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")


def _table_exists(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone() is not None


def migrate_fuel_rates(conn):
    """Kertaluonteinen siirto fuel_rates → surcharge_rates (luku 7.5).

    Jokaisesta kertoimesta tulee rivi: 200 / revenue / percent,
    rate = round((m − 1) × 100, 4). Kerroin ≤ 1 ohitetaan (ei lisää).
    Siirto merkitään schema_migrations-tauluun, joten uudelleenajo ei tee
    mitään — muuten /api/fuel-rates-kautta poistetut rivit palaisivat
    jokaisella käynnistyksellä. Lisäksi samanlaista riviä ei lisätä kahdesti.
    Palauttaa siirrettyjen rivien määrän.
    """
    if not _table_exists(conn, "fuel_rates"):
        return 0
    _ensure_migration_log(conn)
    if conn.execute(
        "SELECT 1 FROM schema_migrations WHERE name = ?", (FUEL_MIGRATION_NAME,)
    ).fetchone():
        return 0

    migrated = 0
    legacy = conn.execute(
        "SELECT valid_from, valid_to, multiplier FROM fuel_rates ORDER BY valid_from, id"
    ).fetchall()
    for valid_from, valid_to, multiplier in legacy:
        if multiplier is None or float(multiplier) <= 1.0:
            continue
        rate = multiplier_to_rate(multiplier)
        exists = conn.execute(
            f"SELECT 1 FROM surcharge_rates WHERE {FUEL_ROW_FILTER} "
            "AND valid_from = ? AND valid_to IS ? AND rate = ?",
            (valid_from, valid_to, rate),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            "INSERT INTO surcharge_rates (service_code, cost_type, rate_type, "
            "rate, valid_from, valid_to) VALUES (?, ?, ?, ?, ?, ?)",
            (FUEL_SERVICE_CODE, FUEL_COST_TYPE, FUEL_RATE_TYPE, rate,
             valid_from, valid_to),
        )
        migrated += 1
    conn.execute(
        "INSERT INTO schema_migrations (name) VALUES (?)", (FUEL_MIGRATION_NAME,)
    )
    return migrated


# ── Apufunktiot ───────────────────────────────────────────────────────

def _norm(value):
    """Tyhjä → None, muuten trimmattu merkkijono."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _norm_upper(value):
    value = _norm(value)
    return value.upper() if value else None


def _to_date(value):
    if isinstance(value, date):
        return value
    if not value:
        raise ValueError("Päivämäärä puuttuu")
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError(f"Virheellinen päivämäärä: {value}") from None


def round_amount(value):
    """Kaksi desimaalia, puolikkaat ylöspäin (luku 4, kohta 7)."""
    return float(Decimal(str(value)).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP))


def derive_trade_type(loading_country, unloading_country):
    """Liikennesuunta lastaus- ja purkumaasta (luku 7.4)."""
    loading = _norm_upper(loading_country)
    unloading = _norm_upper(unloading_country)
    if not loading or not unloading:
        raise ValueError("Lastaus- ja purkumaa ovat pakollisia")
    if loading == HOME_COUNTRY and unloading == HOME_COUNTRY:
        return "DOM"
    if loading == HOME_COUNTRY:
        return "EXP"
    if unloading == HOME_COUNTRY:
        return "IMP"
    return "CROSS"


# ── Haku ──────────────────────────────────────────────────────────────

def _normalize_context(context):
    ctx = dict(context or {})
    cost_type = _norm(ctx.get("cost_type"))
    if cost_type not in COST_TYPES:
        raise ValueError("context.cost_type on pakollinen (revenue/cost)")
    return {
        "cost_type": cost_type,
        "trade_type": _norm_upper(ctx.get("trade_type")),
        "product_type": _norm_upper(ctx.get("product_type")),
        "country": _norm_upper(ctx.get("country")),
        "operator": _norm(ctx.get("operator")),
        "date": _to_date(ctx.get("date")),
        "freight_amount": ctx.get("freight_amount"),
        "chargeable_weight": ctx.get("chargeable_weight"),
        "km": ctx.get("km"),
    }


def _is_valid_on(rate, day):
    if _to_date(rate["valid_from"]) > day:
        return False
    valid_to = rate.get("valid_to")
    return not valid_to or _to_date(valid_to) >= day


def _matches(rate, ctx):
    if rate["cost_type"] != ctx["cost_type"]:
        return False
    for field in ("trade_type", "product_type", "country"):
        value = _norm_upper(rate.get(field))
        if value is not None and value != ctx[field]:
            return False
    operator = _norm(rate.get("operator"))
    if operator is not None and operator != ctx["operator"]:
        return False
    return True


def specificity(rate):
    """Rivin tarkkuuspisteet — täytetyt kohdistuskentät painotettuina."""
    return sum(w for f, w in SPECIFICITY_WEIGHTS.items() if _norm(rate.get(f)))


def select_rate(rates, context):
    """Valitsee tarkimman voimassa olevan, kontekstiin sopivan rivin.

    rates: iteroitava dict-rivejä (yhden palvelukoodin rivit).
    Palauttaa rivin tai None. Tasatilanteessa uusin valid_from, sitten suurin id.
    """
    ctx = _normalize_context(context)  # idempotentti
    candidates = [
        r for r in rates if _matches(r, ctx) and _is_valid_on(r, ctx["date"])
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda r: (specificity(r), str(r["valid_from"]), r.get("id") or 0),
    )


# ── Laskenta ──────────────────────────────────────────────────────────

def compute_amount(rate, context):
    """Laskee lisän summan valitulle riville. Palauttaa (amount, base, capped)."""
    rate_type = rate["rate_type"]
    if rate_type not in RATE_TYPES:
        raise ValueError(f"Tuntematon rate_type: {rate_type}")
    base_field = RATE_TYPE_BASE[rate_type]
    base = None
    price = Decimal(str(rate["rate"]))
    if base_field is None:
        amount = price
    else:
        raw = context.get(base_field)
        if raw is None or raw == "":
            raise ValueError(
                f"{base_field} puuttuu — tarvitaan rate_typelle {rate_type}"
            )
        base = Decimal(str(raw))
        if rate_type == "percent":
            amount = base * price / 100
        elif rate_type == "per_100kg":
            amount = base / 100 * price
        else:  # per_km
            amount = base * price

    capped = None
    min_amount = rate.get("min_amount")
    max_amount = rate.get("max_amount")
    if min_amount is not None and amount < Decimal(str(min_amount)):
        amount = Decimal(str(min_amount))
        capped = "min"
    if max_amount is not None and amount > Decimal(str(max_amount)):
        amount = Decimal(str(max_amount))
        capped = "max"
    return round_amount(amount), (float(base) if base is not None else None), capped


def fetch_rates(conn, service_code, cost_type=None):
    sql = "SELECT * FROM surcharge_rates WHERE service_code = ?"
    params = [str(service_code)]
    if cost_type:
        sql += " AND cost_type = ?"
        params.append(cost_type)
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def calculate_surcharge(service_code, context, conn):
    """Laskee lisän palvelukoodille annetussa kontekstissa.

    context: cost_type (pakollinen), date (pakollinen), trade_type,
    product_type, country, operator, freight_amount, chargeable_weight, km.

    Palauttaa dictin {service_code, cost_type, amount, rate_id, rate_type,
    rate, base, capped} tai None, jos hintaa ei löydy (riviä ei ehdoteta).
    Nostaa ValueErrorin, jos laskentaan tarvittava tieto puuttuu.
    """
    ctx = _normalize_context(context)
    rate = select_rate(fetch_rates(conn, service_code, ctx["cost_type"]), ctx)
    if rate is None:
        return None
    amount, base, capped = compute_amount(rate, ctx)
    return {
        "service_code": str(service_code),
        "cost_type": ctx["cost_type"],
        "amount": amount,
        "rate_id": rate["id"],
        "rate_type": rate["rate_type"],
        "rate": rate["rate"],
        "base": base,
        "capped": capped,
    }


# ── Syötteen validointi (API) ─────────────────────────────────────────

def _opt_number(data, field, errors):
    value = data.get(field)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        errors.append(f"{field} ei ole numero")
        return None


def validate_surcharge_payload(data, conn):
    """Tarkistaa ja normalisoi API-syötteen. Palauttaa (clean, errors)."""
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

    cost_type = _norm(data.get("cost_type"))
    if cost_type not in COST_TYPES:
        errors.append("cost_type on pakollinen (revenue/cost)")
    clean["cost_type"] = cost_type

    for field, allowed in (("trade_type", TRADE_TYPES),
                           ("product_type", PRODUCT_TYPES)):
        value = _norm_upper(data.get(field))
        if value is not None and value not in allowed:
            errors.append(f"{field} ei kelpaa: {value}")
        clean[field] = value

    clean["country"] = _norm_upper(data.get("country"))
    clean["operator"] = _norm(data.get("operator"))

    rate_type = _norm(data.get("rate_type"))
    if rate_type not in RATE_TYPES:
        errors.append(f"rate_type ei kelpaa: {rate_type}")
    clean["rate_type"] = rate_type

    rate = _opt_number(data, "rate", errors)
    if rate is None and "rate ei ole numero" not in errors:
        errors.append("rate puuttuu")
    elif rate is not None and rate < 0:
        errors.append("rate ei voi olla negatiivinen")
    clean["rate"] = rate

    clean["min_amount"] = _opt_number(data, "min_amount", errors)
    clean["max_amount"] = _opt_number(data, "max_amount", errors)
    if (clean["min_amount"] is not None and clean["max_amount"] is not None
            and clean["min_amount"] > clean["max_amount"]):
        errors.append("min_amount ei voi olla suurempi kuin max_amount")

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

    return clean, errors


def find_overlap(conn, clean, exclude_id=None):
    """Etsii rivin, jolla on sama kohdistus ja päällekkäinen voimassaolo."""
    sql = """
        SELECT * FROM surcharge_rates
        WHERE service_code = ? AND cost_type = ?
          AND trade_type IS ? AND product_type IS ?
          AND country IS ? AND operator IS ?
          AND (valid_to IS NULL OR valid_to >= ?)
          AND (? IS NULL OR valid_from <= ?)
    """
    params = [
        clean["service_code"], clean["cost_type"], clean["trade_type"],
        clean["product_type"], clean["country"], clean["operator"],
        clean["valid_from"], clean["valid_to"], clean["valid_to"],
    ]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None

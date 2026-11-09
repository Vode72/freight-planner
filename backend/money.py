"""Rahasummat: ainoa paikka, jossa raha muunnetaan muodosta toiseen (issue #22).

Malli:

* **Kanta** — kokonaisluvut (INTEGER) kiinteällä mittakaavalla:
  - summat ja kiinteät hinnat sentteinä (×100), sarakkeet ``*_cents``
  - yksikköhinnat ja prosentit ×10 000:na, sarakkeet ``*_e4``
    (esim. 12,3456 % → 123456, 1,85 €/km → 18500, 0,60 €/100 kg → 6000)
* **Laskenta** — ``decimal.Decimal``, pyöristys ROUND_HALF_UP.
  Floatia ei käytetä rahalaskennassa.
* **API** — euroina JSON-numeroina (``"amount": 180.0``), kenttien nimet
  ilman mittakaavapäätettä. Decimal muuttuu numeroksi vasta
  JSON-serialisoinnissa (app.MoneyJSONProvider).

SQLitessä ei ole oikeaa desimaalityyppiä: DECIMAL/NUMERIC tallentuu
REALina, ja tekstinä tallennettu desimaali rikkoisi SUM-, vertailu- ja
CHECK-lausekkeet. Kokonaisluvuilla SUM() on tarkka suoraan SQL:ssä.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENTS = 2   # summat: 0,01 €
E4 = 4      # yksikköhinnat ja prosentit: 0,0001

_QUANTS = {CENTS: Decimal("0.01"), E4: Decimal("0.0001")}
_FACTORS = {CENTS: 100, E4: 10_000}

# Taulukohtaiset rahasarakkeet: kannan sarake → (API-kenttä, mittakaava)
MONEY_COLUMNS = {
    "costs": {
        "amount_cents": ("amount", CENTS),
    },
    "trailers": {
        "leasing_rate_cents": ("leasing_rate", CENTS),   # €/päivä
        "rental_rate_cents": ("rental_rate", CENTS),     # €/päivä
    },
    "ferry_rates": {
        "price_cents": ("price", CENTS),
    },
    "km_rates": {
        "domestic_rate_e4": ("domestic_rate", E4),       # €/km
        "continent_rate_e4": ("continent_rate", E4),     # €/km
    },
    "surcharge_rates": {
        "rate_e4": ("rate", E4),     # % / € / €/100 kg / €/km rate_typen mukaan
        "min_amount_cents": ("min_amount", CENTS),
        "max_amount_cents": ("max_amount", CENTS),
    },
    "customer_rate_cards": {
        "freight_price_cents": ("freight_price", CENTS),
    },
    "customer_billing_rules": {
        "rate_e4": ("rate", E4),     # % / € / kate-% (pass_through)
    },
}


# ── Perusmuunnokset ───────────────────────────────────────────────────

def to_decimal(value):
    """Syöte → Decimal. Hyväksyy merkkijonon ("12,50" tai "12.50"), int:n,
    Decimalin ja floatin (lyhin esitys, esim. 0.1 → Decimal("0.1")).

    Tyhjä → None. Virheellinen, NaN, ääretön tai bool → ValueError.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"Ei ole numero: {value!r}")
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, float):
        result = Decimal(repr(value))
    elif isinstance(value, str):
        text = value.strip().replace(" ", "").replace(" ", "").replace(",", ".")
        if not text:
            return None
        try:
            result = Decimal(text)
        except InvalidOperation:
            raise ValueError(f"Ei ole numero: {value!r}") from None
    else:
        raise ValueError(f"Ei ole numero: {value!r}")
    if not result.is_finite():
        raise ValueError(f"Ei ole numero: {value!r}")
    return result


def quantize(value, scale=CENTS):
    """Pyöristys mittakaavaan, puolikkaat ylöspäin (itseisarvoltaan)."""
    value = to_decimal(value)
    if value is None:
        return None
    return value.quantize(_QUANTS[scale], rounding=ROUND_HALF_UP)


def round_money(value):
    """Kaksi desimaalia, ROUND_HALF_UP: 2.675 → 2.68, 0.125 → 0.13."""
    return quantize(value, CENTS)


def to_minor(value, scale=CENTS):
    """Decimal/syöte → kannan kokonaisluku (sentit tai ×10 000)."""
    q = quantize(value, scale)
    if q is None:
        return None
    return int(q.scaleb(scale))


def from_minor(value, scale=CENTS):
    """Kannan kokonaisluku → Decimal (esim. 18000 → Decimal("180.00"))."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Rahasarakkeessa ei-kokonaisluku: {value!r}")
    return Decimal(value).scaleb(-scale).quantize(_QUANTS[scale])


def to_cents(value):
    return to_minor(value, CENTS)


def from_cents(value):
    return from_minor(value, CENTS)


def to_e4(value):
    return to_minor(value, E4)


def from_e4(value):
    return from_minor(value, E4)


def total(values):
    """Decimal-summa (None ohitetaan)."""
    return sum((to_decimal(v) for v in values if v is not None), Decimal("0"))


def percent_of(part, whole, places=2):
    """part / whole × 100, pyöristettynä. whole ≤ 0 → Decimal 0."""
    part, whole = to_decimal(part) or Decimal(0), to_decimal(whole) or Decimal(0)
    if whole <= 0:
        return Decimal(0)
    return (part / whole * 100).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


# ── Rivit: kanta ↔ API/domain ─────────────────────────────────────────

def column(table, field):
    """API-kenttä → kannan sarake (esim. costs.amount → amount_cents)."""
    for db_col, (api_field, _) in MONEY_COLUMNS.get(table, {}).items():
        if api_field == field:
            return db_col
    return field


def columns(table, fields):
    return [column(table, f) for f in fields]


def row_from_db(table, row):
    """Kannan rivi → dict API-kentillä, rahat Decimalina."""
    if row is None:
        return None
    data = dict(row)
    for db_col, (api_field, scale) in MONEY_COLUMNS.get(table, {}).items():
        if db_col in data:
            data[api_field] = from_minor(data.pop(db_col), scale)
    return data


def values_to_db(table, data):
    """dict API-kentillä → dict kannan sarakkeilla, rahat kokonaislukuina."""
    out = dict(data)
    for db_col, (api_field, scale) in MONEY_COLUMNS.get(table, {}).items():
        if api_field in out:
            out[db_col] = to_minor(out.pop(api_field), scale)
    return out


def parse_field(data, field, errors, scale=CENTS, label=None):
    """Valinnainen rahakenttä pyynnöstä → Decimal mittakaavaan pyöristettynä.

    Tyhjä → None. Virheellinen → virheilmoitus listaan ja None.
    """
    value = data.get(field)
    try:
        return quantize(value, scale)
    except ValueError:
        errors.append(f"{label or field} ei ole numero")
        return None

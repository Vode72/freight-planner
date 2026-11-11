"""Kalusto: vetäjät (tractors) ja kaluston yhteiset ominaisuudet.

Ominaisuudet ovat samannimisiä 0/1-sarakkeita sekä ``tractors``- että
``trailers``-taulussa (Alembic 0004). Nimet ovat samat kuin trips- ja
orders-taulujen lipuilla (``adr``, ``tail_lift``, ``temperature_controlled``),
joten sopivuustarkistus on suora vertailu. API:ssa ominaisuudet ovat
molemmilla resursseilla samassa muodossa::

    "features": {"adr": false, "temperature_controlled": true,
                 "tail_lift": false, "crane": false}

Tämä moduuli on ainoa paikka, jossa ominaisuudet, vetäjätyypit, statukset
ja päästöluokat määritellään. Funktiot eivät avaa yhteyksiä eivätkä
commitoi; validointivirheet kerätään listaan (kuten money.parse_field).
"""
from decimal import Decimal, InvalidOperation

# (avain = sarake, suomenkielinen nimi)
FEATURES = [
    ("adr", "ADR"),
    ("temperature_controlled", "Lämpösäätö"),
    ("tail_lift", "Takalaitanostin"),
    ("crane", "Nosturi"),
]
FEATURE_KEYS = [key for key, _ in FEATURES]

VEHICLE_TYPES = ["vetoauto", "kuorma-auto"]
TRUCK_TYPE = "kuorma-auto"  # vain kuorma-autolla on oma kapasiteetti
TRACTOR_STATUSES = ["aktiivinen", "huollossa", "poistettu"]
REMOVED_STATUS = "poistettu"
EMISSION_CLASSES = ["EURO III", "EURO IV", "EURO V", "EEV", "EURO VI"]

# Kapasiteetti: API-kenttä → (nimi virheilmoituksessa, kokonaisluku?)
CAPACITY_FIELDS = {
    "max_weight": ("Maksimipaino (kg)", True),
    "max_ldm": ("Lavametrit (LDM)", False),
    "max_volume": ("Tilavuus (m³)", False),
}

# Trailerityypit, joissa on lämpösäätö (oletus uudelle trailerille)
TEMPERATURE_CONTROLLED_TRAILER_TYPES = {"Umpikaappi", "Sivuaukeava", "Umpikaappi 2-koneinen"}

# Trailerin statukset (Alembic 0005 CHECK). Poistettu = käytöstä poistettu, historia säilyy.
TRAILER_STATUSES = ["Vapaa", "Käytössä", "Huollossa", "Poistettu"]
TRAILER_REMOVED_STATUS = "Poistettu"

# Trailerin kentät, jotka trailers-endpointit tallentavat (järjestys = INSERT/UPDATE)
TRAILER_FIELDS = [
    "plate_number", "identifier", "trailer_type", "leasing_company",
    "leasing_rate_cents", "rental_rate_cents", "status", *FEATURE_KEYS,
]

# Vetäjän muokattavat kentät (järjestys = INSERT/UPDATE)
TRACTOR_FIELDS = [
    "registration_number", "carrier_id", "vehicle_type", "make_model",
    "emission_class", "status", *CAPACITY_FIELDS, *FEATURE_KEYS, "notes",
]


# ── Perusmuunnokset ───────────────────────────────────────────────────

def normalize_registration(value):
    """Rekisterinumero vertailumuotoon: trimmaus, välilyönnit yhdeksi, isot kirjaimet."""
    if value is None:
        return ""
    return " ".join(str(value).split()).upper()


def normalize_plate(value):
    """Trailerin rekisteri: kuten normalize_registration, tyhjä → None (vaihtokori)."""
    return normalize_registration(value) or None


def _blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def parse_bool(value, field, errors):
    """true/false, 1/0 tai "1"/"0"/"true"/"false" → 0/1. Muu → virhe."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and value in (0, 1):
        return value
    if isinstance(value, str) and value.strip().lower() in ("0", "1", "true", "false"):
        return 1 if value.strip().lower() in ("1", "true") else 0
    errors.append(f"{field}: odotettiin true tai false")
    return None


def features_from_row(row):
    """Kannan rivi → {"adr": bool, …}."""
    return {key: bool(row[key]) for key in FEATURE_KEYS}


def default_trailer_features(trailer_type):
    return {key: 0 for key in FEATURE_KEYS} | {
        "temperature_controlled": int(trailer_type in TEMPERATURE_CONTROLLED_TRAILER_TYPES)}


def parse_features(data, errors, base=None):
    """``data["features"]`` → {sarake: 0/1}.

    base: lähtöarvot (olemassa oleva rivi tai tyypin oletus). Puuttuva
    avain säilyttää lähtöarvon; tuntematon avain on virhe.
    """
    values = {key: 0 for key in FEATURE_KEYS} | dict(base or {})
    features = data.get("features")
    if features is None:
        return values
    if not isinstance(features, dict):
        errors.append("features: odotettiin objekti, esim. {\"adr\": true}")
        return values
    unknown = sorted(set(features) - set(FEATURE_KEYS))
    if unknown:
        errors.append(f"features: tuntematon ominaisuus {', '.join(unknown)} "
                      f"(sallitut: {', '.join(FEATURE_KEYS)})")
    for key in FEATURE_KEYS:
        if key in features:
            parsed = parse_bool(features[key], f"features.{key}", errors)
            if parsed is not None:
                values[key] = parsed
    return values


def _parse_positive(value, field, label, integer, errors):
    if _blank(value):
        return None
    if isinstance(value, bool):
        errors.append(f"{label}: ei ole numero")
        return None
    try:
        dec = Decimal(str(value).strip().replace(",", "."))
        if not dec.is_finite():
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        errors.append(f"{label}: ei ole numero")
        return None
    if dec <= 0:
        errors.append(f"{label}: oltava suurempi kuin 0")
        return None
    if integer:
        if dec != dec.to_integral_value():
            errors.append(f"{label}: oltava kokonaisluku")
            return None
        return int(dec)
    return float(dec)  # mitta (ei raha): REAL-sarake


# ── Vetäjä ────────────────────────────────────────────────────────────

def tractor_to_api(row):
    """Kannan rivi (+ carrier_name) → API-muoto, ominaisuudet features-objektina."""
    result = {k: row[k] for k in row.keys() if k not in FEATURE_KEYS}
    result["features"] = features_from_row(row)
    return result


def validate_tractor(data, current=None):
    """Syöte → (kantaan tallennettavat arvot, virheet).

    current: olemassa oleva rivi (PUT). Puuttuvat kentät säilyttävät sen
    arvon, joten PUT voi olla osittainen (esim. pelkkä status). Ilman
    currentia (POST) pakollisia ovat rekisterinumero, carrier ja tyyppi;
    muut saavat oletusarvon (status aktiivinen, ominaisuudet pois).
    Carrierin olemassaoloa ei tarkisteta täällä (vaatii kannan).
    """
    errors = []
    if not isinstance(data, dict):
        return None, ["Puuttuva data"]
    base = dict(current) if current is not None else {
        "registration_number": None, "carrier_id": None, "vehicle_type": None,
        "make_model": None, "emission_class": None, "status": "aktiivinen",
        "max_weight": None, "max_ldm": None, "max_volume": None, "notes": None,
        **{key: 0 for key in FEATURE_KEYS},
    }

    def pick(field):
        return data[field] if field in data else base.get(field)

    values = {}
    reg = normalize_registration(pick("registration_number"))
    if not reg:
        errors.append("Rekisterinumero on pakollinen")
    values["registration_number"] = reg

    carrier_id = pick("carrier_id")
    if _blank(carrier_id):
        errors.append("Kuljetusyhtiö on pakollinen")
        values["carrier_id"] = None
    else:
        try:
            if isinstance(carrier_id, bool):
                raise ValueError
            values["carrier_id"] = int(carrier_id)
        except (TypeError, ValueError):
            errors.append("carrier_id: odotettiin kokonaisluku")
            values["carrier_id"] = None

    vehicle_type = pick("vehicle_type")
    if _blank(vehicle_type):
        errors.append("Tyyppi on pakollinen")
    elif vehicle_type not in VEHICLE_TYPES:
        errors.append(f"vehicle_type: sallitut arvot {', '.join(VEHICLE_TYPES)}")
    values["vehicle_type"] = vehicle_type

    status = pick("status")
    if _blank(status):
        status = "aktiivinen"
    if status not in TRACTOR_STATUSES:
        errors.append(f"status: sallitut arvot {', '.join(TRACTOR_STATUSES)}")
    values["status"] = status

    emission = pick("emission_class")
    if _blank(emission):
        emission = None
    elif emission not in EMISSION_CLASSES:
        errors.append(f"emission_class: sallitut arvot {', '.join(EMISSION_CLASSES)}")
    values["emission_class"] = emission

    for field in ("make_model", "notes"):
        value = pick(field)
        values[field] = None if _blank(value) else str(value).strip()

    for field, (label, integer) in CAPACITY_FIELDS.items():
        values[field] = _parse_positive(pick(field), field, label, integer, errors)
    if vehicle_type != TRUCK_TYPE and any(values[f] is not None for f in CAPACITY_FIELDS):
        if vehicle_type == "vetoauto" and current is not None and "vehicle_type" in data \
                and not any(f in data for f in CAPACITY_FIELDS):
            # kuorma-auto → vetoauto: vanha kapasiteetti tyhjennetään
            values.update({f: None for f in CAPACITY_FIELDS})
        else:
            errors.append("Kapasiteetti (max_weight, max_ldm, max_volume) "
                          "annetaan vain kuorma-autolle")

    values.update(parse_features(data, errors, base={k: base[k] for k in FEATURE_KEYS}))
    return values, errors


# ── Traileri ──────────────────────────────────────────────────────────

def validate_trailer_identity(data, errors, current=None):
    """Rekisteri, tunniste ja status → (plate_number, identifier, status).

    Rekisteri on valinnainen (vaihtokorit), tunniste pakollinen: tyhjä tunniste
    = rekisterinumero. Puuttuva avain säilyttää currentin arvon (PUT).
    Yksikäsitteisyys tarkistetaan kannasta (app._trailer_conflict).
    """
    def pick(field):
        if field in data:
            return data[field]
        return current[field] if current is not None else None

    plate = normalize_plate(pick("plate_number"))
    identifier = pick("identifier")
    identifier = None if _blank(identifier) else str(identifier).strip()
    if identifier is None:
        identifier = plate
    if identifier is None:
        errors.append("Rekisterinumero tai tunniste on pakollinen")
    status = pick("status")
    if _blank(status):
        status = "Vapaa"
    elif status not in TRAILER_STATUSES:
        errors.append(f"status: sallitut arvot {', '.join(TRAILER_STATUSES)}")
    return plate, identifier, status


def meta():
    """Koodistot käyttöliittymälle (GET /api/equipment-meta)."""
    return {
        "features": [{"key": key, "label": label} for key, label in FEATURES],
        "vehicle_types": VEHICLE_TYPES,
        "tractor_statuses": TRACTOR_STATUSES,
        "trailer_statuses": TRAILER_STATUSES,
        "emission_classes": EMISSION_CLASSES,
        "capacity_fields": [{"key": key, "label": label}
                            for key, (label, _) in CAPACITY_FIELDS.items()],
    }

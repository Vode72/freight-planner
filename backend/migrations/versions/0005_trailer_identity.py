"""trailerien yksikäsitteisyys: rekisteri/tunniste uniikki, huoltohistoria id:hen, Poistettu-status

* ``trailers.plate_number`` on valinnainen (vaihtokoreilla ei rekisteriä), tallennetaan
  normalisoituna (trimmaus, välilyönnit yhdeksi, isot kirjaimet) ja on uniikki kun ei NULL
  (osittainen indeksi, COLLATE NOCASE).
* ``trailers.identifier`` on pakollinen ja uniikki (COLLATE NOCASE). Tyhjä tunniste
  täytetään rekisterinumerolla; täytetyt rivit tulostetaan. Jos täyttö törmää
  olemassa olevaan tunnisteeseen, se on todellinen tupla.
* ``trailers.status``: Vapaa / Käytössä / Huollossa / Poistettu (CHECK). Tyhjä → Vapaa.
* ``trailer_maintenance.trailer_id`` viittasi trailerin rekisterinumeroon tekstinä
  (rekisterin muutos irrotti historian, poisto jätti orpoja rivejä). Nyt INTEGER FK
  → ``trailers.id``; rivit yhdistetään normalisoidulla rekisterillä.

Migraatio pysähtyy (ValueError, ei muutoksia) jos kannassa on:
  rekisteri- tai tunnistetuplia, traileri ilman rekisteriä ja tunnistetta,
  tuntematon status tai orpoja huoltorivejä (virhe tulostaa siivous-SQL:n).

Downgrade (→ 0004) pysähtyy, jos kannassa on rekisterittömiä trailereita: vanha
huoltohistoria ja skeema vaativat rekisterin.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-11
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

# Jäädytetyt kopiot (equipment.py voi muuttua, tämä revisio ei)
TRAILER_STATUSES = ("Vapaa", "Käytössä", "Huollossa", "Poistettu")
FEATURE_COLUMNS = ("adr", "temperature_controlled", "tail_lift", "crane")

TRAILER_COLUMNS = (
    "id", "plate_number", "identifier", "trailer_type", "leasing_company",
    "leasing_rate_cents", "rental_rate_cents", "status",
    "inspection_date", "inspection_due", "refrigeration_service_date",
    "refrigeration_service_due", "refrigeration_service_interval_months",
    "maintenance_notes", *FEATURE_COLUMNS,
)
MAINTENANCE_COLUMNS = ("id", "trailer_id", "maintenance_type", "date", "next_due",
                       "notes", "created_at")


def _int(col, extra=""):
    return f"{col} INTEGER{extra} CHECK ({col} IS NULL OR typeof({col}) = 'integer')"


def _flag(col):
    return f"{col} INTEGER NOT NULL DEFAULT 0 CHECK ({col} IN (0, 1))"


_STATUS_LIST = ", ".join(f"'{s}'" for s in TRAILER_STATUSES)

NEW_TRAILERS_DDL = f"""
CREATE TABLE {{name}} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT CHECK (plate_number IS NULL OR length(trim(plate_number)) > 0),
    identifier TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK (length(trim(identifier)) > 0),
    trailer_type TEXT NOT NULL,
    leasing_company TEXT DEFAULT 'Demo Trailer Leasing Oy',
    {_int("leasing_rate_cents", " DEFAULT 0")},
    {_int("rental_rate_cents", " DEFAULT 0")},
    status TEXT NOT NULL DEFAULT 'Vapaa' CHECK (status IN ({_STATUS_LIST})),
    inspection_date TEXT,
    inspection_due TEXT,
    refrigeration_service_date TEXT,
    refrigeration_service_due TEXT,
    refrigeration_service_interval_months INTEGER DEFAULT 6,
    maintenance_notes TEXT,
    {_flag("adr")},
    {_flag("temperature_controlled")},
    {_flag("tail_lift")},
    {_flag("crane")}
)"""

# 0004:n skeema: 0003:n taulu + ALTER TABLE ADD COLUMN -sarakkeet
OLD_TRAILERS_DDL = f"""
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
    maintenance_notes TEXT, {_flag("adr")}, {_flag("temperature_controlled")}, \
{_flag("tail_lift")}, {_flag("crane")})"""

NEW_MAINTENANCE_DDL = """
CREATE TABLE {name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trailer_id INTEGER NOT NULL REFERENCES trailers(id) CHECK (typeof(trailer_id) = 'integer'),
    maintenance_type TEXT NOT NULL,
    date TEXT NOT NULL,
    next_due TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
)"""

OLD_MAINTENANCE_DDL = """
CREATE TABLE {name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trailer_id TEXT NOT NULL REFERENCES trailers(plate_number),
    maintenance_type TEXT NOT NULL,
    date TEXT NOT NULL,
    next_due TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
)"""

NEW_INDEXES = [
    "CREATE UNIQUE INDEX idx_trailers_plate_number ON trailers (plate_number COLLATE NOCASE) "
    "WHERE plate_number IS NOT NULL",
    "CREATE INDEX idx_trailer_maintenance_trailer ON trailer_maintenance (trailer_id)",
]


def normalize_plate(value):
    """Sama sääntö kuin equipment.normalize_registration (jäädytetty kopio). Tyhjä → None."""
    if value is None:
        return None
    text = " ".join(str(value).split()).upper()
    return text or None


def _clean(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _fold(value):
    """Vertailuavain: COLLATE NOCASE -tyylinen kirjainkoosta riippumaton."""
    return value.casefold()


def _sql_list(values):
    return ", ".join(str(v) for v in values)


def _rebuild(bind, table, ddl, columns, rows):
    """Luo taulun uudelleen annetuilla riveillä; AUTOINCREMENT-laskuri säilyy."""
    tmp = f"{table}__new"
    bind.exec_driver_sql(f"DROP TABLE IF EXISTS {tmp}")
    bind.exec_driver_sql(ddl.format(name=tmp))
    insert = (f"INSERT INTO {tmp} ({', '.join(columns)}) "
              f"VALUES ({', '.join('?' * len(columns))})")
    for row in rows:
        bind.exec_driver_sql(insert, tuple(row[c] for c in columns))
    seq = bind.exec_driver_sql(
        "SELECT seq FROM sqlite_sequence WHERE name = ?", (table,)).fetchone()
    bind.exec_driver_sql(f"DROP TABLE {table}")
    bind.exec_driver_sql(f"ALTER TABLE {tmp} RENAME TO {table}")
    if seq is not None:
        bind.exec_driver_sql("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        bind.exec_driver_sql(
            "INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table, seq[0]))


def _rows(bind, table, columns):
    result = bind.exec_driver_sql(f"SELECT {', '.join(columns)} FROM {table} ORDER BY id")
    return [dict(zip(columns, r)) for r in result]


def _prepare_trailers(trailers):
    """Normalisoi rivit ja kerää ongelmat. Palauttaa (rivit, täytetyt, ongelmat)."""
    problems, filled = [], []
    for row in trailers:
        row["plate_number"] = normalize_plate(row["plate_number"])
        identifier = _clean(row["identifier"])
        if identifier is None:
            if row["plate_number"] is None:
                problems.append(f"  traileri id={row['id']}: ei rekisteriä eikä tunnistetta")
                continue
            identifier = row["plate_number"]
            filled.append(row)
        row["identifier"] = identifier
        if _clean(row["status"]) is None:
            row["status"] = "Vapaa"
        elif row["status"] not in TRAILER_STATUSES:
            problems.append(f"  traileri id={row['id']}: tuntematon status {row['status']!r} "
                            f"(sallitut: {', '.join(TRAILER_STATUSES)})")

    for field, label in (("plate_number", "Rekisterinumero"), ("identifier", "Tunniste")):
        groups = {}
        for row in trailers:
            if row[field] is not None:
                groups.setdefault(_fold(row[field]), []).append(row)
        for dupes in groups.values():
            if len(dupes) > 1:
                desc = ", ".join(f"id={r['id']}" + (" (tunniste täytetty rekisteristä)"
                                                     if r in filled and field == "identifier" else "")
                                 for r in dupes)
                problems.append(f"  {label} {dupes[0][field]} on usealla trailerilla: {desc}")
    return filled, problems


def upgrade():
    bind = op.get_bind()
    trailers = _rows(bind, "trailers", TRAILER_COLUMNS)
    maintenance = _rows(bind, "trailer_maintenance", MAINTENANCE_COLUMNS)
    filled, problems = _prepare_trailers(trailers)

    by_plate = {_fold(r["plate_number"]): r["id"] for r in trailers if r["plate_number"]}
    orphans = []
    for row in maintenance:
        plate = normalize_plate(row["trailer_id"])
        trailer_id = by_plate.get(_fold(plate)) if plate else None
        if trailer_id is None:
            orphans.append(dict(row))
        row["trailer_id"] = trailer_id
    if orphans:
        problems.append("  Orpoja huoltorivejä (rekisterille ei löydy traileria):")
        problems += [f"    trailer_maintenance id={r['id']}: {r['maintenance_type']} "
                     f"{r['date']}, rekisteri {r['trailer_id']!r}" for r in orphans]
        orphan_ids = [r["id"] for r in orphans]
        problems.append("  Siivous (tarkista ensin, poisto on pysyvä):\n"
                        f"    DELETE FROM trailer_maintenance WHERE id IN ({_sql_list(orphan_ids)});")
    if problems:
        raise ValueError("Migraatio 0005 pysähtyi, kanta ennallaan. Korjaa ensin:\n"
                         + "\n".join(problems))

    for row in filled:
        print(f"0005: trailerin id={row['id']} tyhjä tunniste täytetty rekisterillä "
              f"{row['plate_number']}")

    _rebuild(bind, "trailers", NEW_TRAILERS_DDL, TRAILER_COLUMNS, trailers)
    _rebuild(bind, "trailer_maintenance", NEW_MAINTENANCE_DDL, MAINTENANCE_COLUMNS, maintenance)
    for sql in NEW_INDEXES:
        bind.exec_driver_sql(sql)


def downgrade():
    bind = op.get_bind()
    trailers = _rows(bind, "trailers", TRAILER_COLUMNS)
    without_plate = [r for r in trailers if r["plate_number"] is None]
    if without_plate:
        listed = ", ".join(f"id={r['id']} ({r['identifier']})" for r in without_plate)
        raise ValueError(
            f"Downgrade 0005 → 0004 pysähtyi, kanta ennallaan: {len(without_plate)} traileria "
            f"ilman rekisterinumeroa ({listed}). Revisio 0004 vaatii rekisterin "
            f"(myös huoltohistoria viittaa siihen). Anna rekisteri tai poista trailerit ensin.")
    plates = {r["id"]: r["plate_number"] for r in trailers}
    maintenance = _rows(bind, "trailer_maintenance", MAINTENANCE_COLUMNS)
    for row in maintenance:
        row["trailer_id"] = plates[row["trailer_id"]]

    bind.exec_driver_sql("DROP INDEX IF EXISTS idx_trailers_plate_number")
    bind.exec_driver_sql("DROP INDEX IF EXISTS idx_trailer_maintenance_trailer")
    _rebuild(bind, "trailers", OLD_TRAILERS_DDL, TRAILER_COLUMNS, trailers)
    _rebuild(bind, "trailer_maintenance", OLD_MAINTENANCE_DDL, MAINTENANCE_COLUMNS, maintenance)

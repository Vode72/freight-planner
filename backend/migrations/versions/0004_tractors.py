"""vetäjärekisteri: tractors-taulu, kaluston ominaisuudet, trips.tractor_id

* ``tractors`` korvaa vanhan ``trucks``-taulun: rekisterinumero (uniikki),
  carrier (pakollinen), tyyppi (vetoauto / kuorma-auto), merkki ja malli,
  päästöluokka, status (aktiivinen / huollossa / poistettu), kuorma-autolle
  kapasiteetti (max_weight kg, max_ldm, max_volume m³) ja ominaisuudet.
* Ominaisuudet ovat samannimisiä 0/1-sarakkeita sekä vetäjillä että
  trailereilla (``adr``, ``temperature_controlled``, ``tail_lift``,
  ``crane``) — samat nimet kuin trips- ja orders-taulujen lipuilla.
  Olemassa oleville trailereille ``temperature_controlled`` päätellään
  trailerityypistä.
* ``trips.tractor_id`` (nullable FK). Vanhat tripit linkitetään, kun
  ``truck_plate`` ja ``carrier_id`` vastaavat siirrettyä vetäjää.
  ``truck_plate`` jää tripille rekisterinumeron kopioksi (dokumentit).
* ``trucks``-rivit siirretään vetoautoiksi (sama id) ja taulu poistetaan.
  Saman carrierin tuplarekisterit yhdistetään; sama rekisteri eri
  carriereilla keskeyttää migraation (korjattava käsin).

Downgrade palauttaa ``trucks``-taulun vetäjistä ja poistaa uudet sarakkeet
(SQLite ≥ 3.35: ALTER TABLE … DROP COLUMN).

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-11
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

# Jäädytetyt kopiot (equipment.py voi muuttua, tämä revisio ei)
FEATURE_COLUMNS = ("adr", "temperature_controlled", "tail_lift", "crane")
TEMPERATURE_CONTROLLED_TRAILER_TYPES = ("Umpikaappi", "Sivuaukeava", "Umpikaappi 2-koneinen")
TRUCK_STATUS_TO_TRACTOR = {"Vapaa": "aktiivinen", "Ajossa": "aktiivinen", "Huollossa": "huollossa",
                           "Poistettu": "poistettu"}  # Poistettu: vain downgrade-kierros
TRACTOR_STATUS_TO_TRUCK = {"aktiivinen": "Vapaa", "huollossa": "Huollossa", "poistettu": "Poistettu"}


def _flag(col):
    return f"{col} INTEGER NOT NULL DEFAULT 0 CHECK ({col} IN (0, 1))"


TRACTORS_DDL = f"""
CREATE TABLE tractors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_number TEXT NOT NULL COLLATE NOCASE UNIQUE
        CHECK (length(trim(registration_number)) > 0),
    carrier_id INTEGER NOT NULL REFERENCES carriers(id),
    vehicle_type TEXT NOT NULL DEFAULT 'vetoauto'
        CHECK (vehicle_type IN ('vetoauto', 'kuorma-auto')),
    make_model TEXT,
    emission_class TEXT,
    status TEXT NOT NULL DEFAULT 'aktiivinen'
        CHECK (status IN ('aktiivinen', 'huollossa', 'poistettu')),
    max_weight INTEGER CHECK (max_weight IS NULL OR max_weight > 0),
    max_ldm REAL CHECK (max_ldm IS NULL OR max_ldm > 0),
    max_volume REAL CHECK (max_volume IS NULL OR max_volume > 0),
    {_flag("adr")},
    {_flag("temperature_controlled")},
    {_flag("tail_lift")},
    {_flag("crane")},
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    CHECK (vehicle_type = 'kuorma-auto'
           OR (max_weight IS NULL AND max_ldm IS NULL AND max_volume IS NULL))
)"""

TRUCKS_DDL = """
CREATE TABLE trucks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL,
    carrier_id INTEGER NOT NULL,
    status TEXT DEFAULT 'Vapaa',
    FOREIGN KEY (carrier_id) REFERENCES carriers(id)
)"""


def normalize_registration(value):
    """Sama sääntö kuin equipment.normalize_registration (jäädytetty kopio)."""
    if value is None:
        return ""
    return " ".join(str(value).split()).upper()


def _exists(bind, kind, name):
    return bind.exec_driver_sql(
        "SELECT 1 FROM sqlite_master WHERE type = ? AND name = ?", (kind, name)
    ).fetchone() is not None


def _columns(bind, table):
    return {r[1] for r in bind.exec_driver_sql(f"PRAGMA table_info({table})")}


def _keep_sequence(bind, src, dst):
    seq = bind.exec_driver_sql(
        "SELECT seq FROM sqlite_sequence WHERE name = ?", (src,)).fetchone()
    if seq is None:
        return
    bind.exec_driver_sql("DELETE FROM sqlite_sequence WHERE name = ?", (dst,))
    bind.exec_driver_sql(
        "INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (dst, seq[0]))


def _copy_trucks(bind):
    """trucks → tractors (vetoauto, sama id). Palauttaa ohitetut tuplat."""
    rows = bind.exec_driver_sql(
        "SELECT id, plate_number, carrier_id, status FROM trucks ORDER BY id").fetchall()
    seen = {}  # normalisoitu rekisteri → carrier_id
    for truck_id, plate, carrier_id, status in rows:
        reg = normalize_registration(plate)
        if not reg:
            raise ValueError(f"trucks.plate_number (id={truck_id}): tyhjä rekisterinumero")
        if reg in seen:
            if seen[reg] != carrier_id:
                raise ValueError(
                    f"trucks.plate_number (id={truck_id}): rekisterinumero {reg} on "
                    f"usealla kuljetusyhtiöllä — korjaa ennen migraatiota")
            continue  # saman carrierin tupla: tripit linkittyvät rekisterillä
        seen[reg] = carrier_id
        bind.exec_driver_sql(
            "INSERT INTO tractors (id, registration_number, carrier_id, vehicle_type, status) "
            "VALUES (?, ?, ?, 'vetoauto', ?)",
            (truck_id, reg, carrier_id, TRUCK_STATUS_TO_TRACTOR.get(status, "aktiivinen")))
    _keep_sequence(bind, "trucks", "tractors")


def _link_trips(bind):
    if not {"truck_plate", "carrier_id"} <= _columns(bind, "trips"):
        return  # hyvin vanha kanta: ei mitään linkitettävää
    trips = bind.exec_driver_sql(
        "SELECT id, truck_plate, carrier_id FROM trips "
        "WHERE truck_plate IS NOT NULL AND carrier_id IS NOT NULL").fetchall()
    for trip_id, plate, carrier_id in trips:
        tractor = bind.exec_driver_sql(
            "SELECT id FROM tractors WHERE registration_number = ? AND carrier_id = ?",
            (normalize_registration(plate), carrier_id)).fetchone()
        if tractor:
            bind.exec_driver_sql(
                "UPDATE trips SET tractor_id = ? WHERE id = ?", (tractor[0], trip_id))


def upgrade():
    bind = op.get_bind()
    bind.exec_driver_sql(TRACTORS_DDL)
    bind.exec_driver_sql("CREATE INDEX idx_tractors_carrier ON tractors (carrier_id)")

    existing = _columns(bind, "trailers")
    for col in FEATURE_COLUMNS:
        if col not in existing:
            bind.exec_driver_sql(f"ALTER TABLE trailers ADD COLUMN {_flag(col)}")
    if "trailer_type" in existing:
        placeholders = ", ".join("?" * len(TEMPERATURE_CONTROLLED_TRAILER_TYPES))
        bind.exec_driver_sql(
            f"UPDATE trailers SET temperature_controlled = 1 "
            f"WHERE trailer_type IN ({placeholders})", TEMPERATURE_CONTROLLED_TRAILER_TYPES)

    bind.exec_driver_sql(
        "ALTER TABLE trips ADD COLUMN tractor_id INTEGER REFERENCES tractors(id)")
    bind.exec_driver_sql("CREATE INDEX idx_trips_tractor ON trips (tractor_id)")

    if _exists(bind, "table", "trucks"):
        _copy_trucks(bind)
        bind.exec_driver_sql("DROP TABLE trucks")
    _link_trips(bind)


def downgrade():
    bind = op.get_bind()
    bind.exec_driver_sql(TRUCKS_DDL)
    for tractor_id, reg, carrier_id, status in bind.exec_driver_sql(
            "SELECT id, registration_number, carrier_id, status FROM tractors ORDER BY id"):
        bind.exec_driver_sql(
            "INSERT INTO trucks (id, plate_number, carrier_id, status) VALUES (?, ?, ?, ?)",
            (tractor_id, reg, carrier_id, TRACTOR_STATUS_TO_TRUCK.get(status, "Vapaa")))
    _keep_sequence(bind, "tractors", "trucks")

    bind.exec_driver_sql("DROP INDEX IF EXISTS idx_trips_tractor")
    bind.exec_driver_sql("ALTER TABLE trips DROP COLUMN tractor_id")
    for col in FEATURE_COLUMNS:
        bind.exec_driver_sql(f"ALTER TABLE trailers DROP COLUMN {col}")
    bind.exec_driver_sql("DROP TABLE tractors")

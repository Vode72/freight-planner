"""viitedata: palvelukoodisto, oletusasetukset ja polttoainelisän siirto

Kertaluonteiset datamuutokset, jotka ennen Alembicia tehtiin
migrate_*.py-skripteissä ja app.migrate_db():ssä. Kaikki idempotentteja:

* services: koodisto (services.SERVICES) ja vanhojen koodien yhdistäminen
  401→400, 831→830 costs-riveillä,
* settings: oletusasetukset (olemassa oleviin arvoihin ei kosketa),
* fuel_rates → surcharge_rates (spec 7.5), jos vanhassa taulussa on rivejä
  eikä siirtoa ole jo merkitty schema_migrations-tauluun.

Demodata ei kuulu migraatioihin: se tulee init_db.seed_demo_data():sta
(python reset_demo.py).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-09
"""
from decimal import Decimal, ROUND_HALF_UP

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SETTINGS_DEFAULTS = [
    ("forwarder_name",        "Demo Freight Oy"),
    ("forwarder_address",     "Logistiikkakatu 1, 00100 Helsinki"),
    ("forwarder_phone",       "+358 9 1234567"),
    ("forwarder_email",       "info@demofreight.fi"),
    ("forwarder_vat",         "FI12345678"),
    ("forwarder_business_id", "1234567-8"),
    ("alert_inspection_days",    "30"),
    ("alert_refrigeration_days", "30"),
    ("alert_load_pct",           "90"),
    ("alert_late_hours",         "2"),
    ("alert_inspection_enabled",    "1"),
    ("alert_refrigeration_enabled", "1"),
    ("alert_load_enabled",          "1"),
    ("alert_late_enabled",          "1"),
]

LEGACY_CODE_MAP = {"401": "400", "831": "830"}
FUEL_MIGRATION_NAME = "fuel_rates_to_surcharge_rates"
FUEL_ROW_FILTER = (
    "service_code = '200' AND cost_type = 'revenue' AND rate_type = 'percent' "
    "AND trade_type IS NULL AND product_type IS NULL "
    "AND country IS NULL AND operator IS NULL"
)


def _services(bind):
    # Koodisto luetaan koodista: se on viitedataa, jonka db_migrate
    # synkronoi myös jokaisen upgraden jälkeen.
    from services import SERVICES
    for code, name, category, default_cost_type in SERVICES:
        bind.exec_driver_sql(
            "INSERT INTO services (code, name, category, default_cost_type, active) "
            "VALUES (?, ?, ?, ?, 1) ON CONFLICT(code) DO NOTHING",
            (code, name, category, default_cost_type),
        )
    for old, new in LEGACY_CODE_MAP.items():
        bind.exec_driver_sql("DELETE FROM services WHERE code = ?", (old,))
        bind.exec_driver_sql("UPDATE costs SET cost_code = ? WHERE cost_code = ?", (new, old))


def _settings(bind):
    for key, value in SETTINGS_DEFAULTS:
        bind.exec_driver_sql(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO NOTHING",
            (key, value),
        )


def _fuel_rates(bind):
    done = bind.exec_driver_sql(
        "SELECT 1 FROM schema_migrations WHERE name = ?", (FUEL_MIGRATION_NAME,)
    ).fetchone()
    legacy = bind.exec_driver_sql(
        "SELECT valid_from, valid_to, multiplier FROM fuel_rates ORDER BY valid_from, id"
    ).fetchall()
    if done or not legacy:
        return
    for valid_from, valid_to, multiplier in legacy:
        if multiplier is None:
            continue
        m = Decimal(str(multiplier))
        if m <= 1:
            continue
        rate = ((m - 1) * 100).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        # Sarake on tässä revisiossa vielä REAL; 0003 muuntaa kokonaisluvuksi.
        exists = bind.exec_driver_sql(
            f"SELECT 1 FROM surcharge_rates WHERE {FUEL_ROW_FILTER} "
            "AND valid_from = ? AND valid_to IS ? AND rate = ?",
            (valid_from, valid_to, float(rate)),
        ).fetchone()
        if exists:
            continue
        bind.exec_driver_sql(
            "INSERT INTO surcharge_rates (service_code, cost_type, rate_type, rate, "
            "valid_from, valid_to) VALUES ('200', 'revenue', 'percent', ?, ?, ?)",
            (float(rate), valid_from, valid_to),
        )
    bind.exec_driver_sql(
        "INSERT INTO schema_migrations (name) VALUES (?)", (FUEL_MIGRATION_NAME,)
    )


def upgrade():
    bind = op.get_bind()
    _services(bind)
    _settings(bind)
    _fuel_rates(bind)


def downgrade():
    # Datamuutoksia ei peruta: koodiston ja asetusten rivit ovat harmittomia
    # vanhalle skeemalle, ja 401/831-koodeja ei enää ole.
    pass

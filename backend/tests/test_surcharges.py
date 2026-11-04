"""Lisähinnat (surcharge_rates) — laskenta, hakujärjestys, voimassaolo, CRUD.

Määrittely: docs/pricing-engine-spec.md, luku 7. Kaikki hinnat ovat demodataa.
"""
import sqlite3
from datetime import date

import pytest

from surcharges import (
    DEMO_SURCHARGE_RATES, SURCHARGE_COLUMNS, calculate_surcharge,
    derive_trade_type, ensure_surcharge_rates, round_amount,
    run_surcharges_migration, select_rate, specificity,
)

DAY = "2026-06-15"


@pytest.fixture
def conn():
    """Tyhjä surcharge_rates-taulu muistikannassa (ei demodataa)."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    ensure_surcharge_rates(c)
    yield c
    c.close()


def add_rate(conn, **kw):
    row = {
        "service_code": "530", "cost_type": "revenue", "trade_type": None,
        "product_type": None, "country": None, "operator": None,
        "rate_type": "fixed", "rate": 100, "min_amount": None,
        "max_amount": None, "valid_from": "2026-01-01", "valid_to": None,
    }
    row.update(kw)
    cur = conn.execute(
        f"INSERT INTO surcharge_rates ({', '.join(SURCHARGE_COLUMNS)}) "
        f"VALUES ({', '.join('?' * len(SURCHARGE_COLUMNS))})",
        [row[c] for c in SURCHARGE_COLUMNS],
    )
    return cur.lastrowid


def ctx(**kw):
    base = {"cost_type": "revenue", "date": DAY}
    base.update(kw)
    return base


# ── derive_trade_type ─────────────────────────────────────────────────

@pytest.mark.parametrize("loading, unloading, expected", [
    ("FI", "FI", "DOM"),
    ("FI", "BE", "EXP"),
    ("DE", "FI", "IMP"),
    ("DE", "BE", "CROSS"),
    (" fi ", "be", "EXP"),
])
def test_derive_trade_type(loading, unloading, expected):
    assert derive_trade_type(loading, unloading) == expected


@pytest.mark.parametrize("loading, unloading", [(None, "FI"), ("FI", ""), ("", None)])
def test_derive_trade_type_requires_both_countries(loading, unloading):
    with pytest.raises(ValueError):
        derive_trade_type(loading, unloading)


# ── rate_typet ────────────────────────────────────────────────────────

def test_percent_is_calculated_from_freight(conn):
    add_rate(conn, service_code="230", rate_type="percent", rate=9)
    res = calculate_surcharge("230", ctx(freight_amount=2000), conn)
    assert res["amount"] == 180.00
    assert res["rate_type"] == "percent"
    assert res["base"] == 2000
    assert res["capped"] is None


def test_fixed_ignores_bases(conn):
    add_rate(conn, rate_type="fixed", rate=150)
    res = calculate_surcharge("530", ctx(freight_amount=99999, km=5000), conn)
    assert res["amount"] == 150.00
    assert res["base"] is None


def test_per_100kg_uses_chargeable_weight(conn):
    add_rate(conn, service_code="540", rate_type="per_100kg", rate=0.40)
    res = calculate_surcharge("540", ctx(chargeable_weight=3250), conn)
    assert res["amount"] == 13.00  # 3250 / 100 × 0,40


def test_per_km(conn):
    add_rate(conn, service_code="300", cost_type="cost", rate_type="per_km", rate=0.20)
    res = calculate_surcharge("300", ctx(cost_type="cost", km=1234), conn)
    assert res["amount"] == 246.80


@pytest.mark.parametrize("rate_type, missing", [
    ("percent", "freight_amount"),
    ("per_100kg", "chargeable_weight"),
    ("per_km", "km"),
])
def test_missing_base_raises_value_error(conn, rate_type, missing):
    add_rate(conn, rate_type=rate_type, rate=1)
    with pytest.raises(ValueError, match=missing):
        calculate_surcharge("530", ctx(), conn)


def test_missing_cost_type_or_date_raises(conn):
    add_rate(conn)
    with pytest.raises(ValueError, match="cost_type"):
        calculate_surcharge("530", {"date": DAY}, conn)
    with pytest.raises(ValueError):
        calculate_surcharge("530", {"cost_type": "revenue"}, conn)


def test_rounding_half_up():
    assert round_amount(0.125) == 0.13
    assert round_amount(2.675) == 2.68  # float-pyöristys antaisi 2.67
    assert round_amount(1.005) == 1.01


def test_percent_rounding_half_up(conn):
    add_rate(conn, rate_type="percent", rate=2.5)
    # 100,50 × 2,5 % = 2,5125 → 2,51 ; 100,30 × 2,5 % = 2,5075 → 2,51
    assert calculate_surcharge("530", ctx(freight_amount=100.5), conn)["amount"] == 2.51
    assert calculate_surcharge("530", ctx(freight_amount=100.3), conn)["amount"] == 2.51


# ── min / max ─────────────────────────────────────────────────────────

def test_min_amount_applies(conn):
    add_rate(conn, rate_type="per_100kg", rate=0.40, min_amount=5)
    res = calculate_surcharge("530", ctx(chargeable_weight=500), conn)  # 2,00
    assert res["amount"] == 5.00
    assert res["capped"] == "min"


def test_max_amount_applies(conn):
    add_rate(conn, rate_type="percent", rate=10, max_amount=150)
    res = calculate_surcharge("530", ctx(freight_amount=2000), conn)  # 200
    assert res["amount"] == 150.00
    assert res["capped"] == "max"


def test_amount_between_min_and_max_unchanged(conn):
    add_rate(conn, rate_type="percent", rate=10, min_amount=50, max_amount=300)
    res = calculate_surcharge("530", ctx(freight_amount=2000), conn)
    assert res["amount"] == 200.00
    assert res["capped"] is None


def test_min_equal_boundary_not_capped(conn):
    add_rate(conn, rate_type="fixed", rate=50, min_amount=50, max_amount=50)
    res = calculate_surcharge("530", ctx(), conn)
    assert res["amount"] == 50.00
    assert res["capped"] is None


# ── Hakujärjestys (luku 7.3) ──────────────────────────────────────────

def test_no_rate_returns_none(conn):
    assert calculate_surcharge("530", ctx(), conn) is None


def test_most_specific_wins(conn):
    add_rate(conn, trade_type="EXP", rate=10)
    add_rate(conn, trade_type="EXP", country="BE", rate=20)
    best = add_rate(conn, trade_type="EXP", product_type="FTL", country="BE", rate=30)
    res = calculate_surcharge(
        "530", ctx(trade_type="EXP", product_type="FTL", country="BE"), conn)
    assert res["rate_id"] == best
    assert res["amount"] == 30.00


def test_direction_plus_country_beats_direction(conn):
    add_rate(conn, trade_type="EXP", rate=10)
    add_rate(conn, trade_type="EXP", country="BE", rate=20)
    res = calculate_surcharge(
        "530", ctx(trade_type="EXP", product_type="LTL", country="BE"), conn)
    assert res["amount"] == 20.00


def test_country_beats_product(conn):
    add_rate(conn, trade_type="EXP", product_type="FTL", rate=10)
    add_rate(conn, trade_type="EXP", country="BE", rate=20)
    res = calculate_surcharge(
        "530", ctx(trade_type="EXP", product_type="FTL", country="BE"), conn)
    assert res["amount"] == 20.00


def test_falls_back_to_direction_for_other_country(conn):
    add_rate(conn, trade_type="EXP", rate=10)
    add_rate(conn, trade_type="EXP", country="BE", rate=20)
    res = calculate_surcharge("530", ctx(trade_type="EXP", country="DE"), conn)
    assert res["amount"] == 10.00


def test_non_matching_targeting_excluded(conn):
    add_rate(conn, trade_type="IMP", rate=10)
    add_rate(conn, trade_type="EXP", product_type="LTL", rate=20)
    add_rate(conn, trade_type="EXP", country="NL", rate=30)
    assert calculate_surcharge(
        "530", ctx(trade_type="EXP", product_type="FTL", country="BE"), conn) is None


def test_operator_specific_beats_general(conn):
    add_rate(conn, rate=150)
    add_rate(conn, operator="Demo Ferries", rate=180)
    assert calculate_surcharge("530", ctx(operator="Demo Ferries"), conn)["amount"] == 180
    assert calculate_surcharge("530", ctx(operator="Baltic Demo Line"), conn)["amount"] == 150
    assert calculate_surcharge("530", ctx(), conn)["amount"] == 150


def test_cost_type_separates_sales_and_purchase(conn):
    add_rate(conn, cost_type="revenue", rate=150)
    add_rate(conn, cost_type="cost", rate=180)
    assert calculate_surcharge("530", ctx(cost_type="revenue"), conn)["amount"] == 150
    assert calculate_surcharge("530", ctx(cost_type="cost"), conn)["amount"] == 180


def test_cost_type_does_not_fall_back(conn):
    add_rate(conn, cost_type="revenue", rate=150)
    assert calculate_surcharge("530", ctx(cost_type="cost"), conn) is None


def test_service_code_isolated(conn):
    add_rate(conn, service_code="520", rate=300)
    assert calculate_surcharge("530", ctx(), conn) is None


def test_context_is_case_insensitive(conn):
    add_rate(conn, trade_type="EXP", country="BE", product_type="FTL", rate=30)
    res = calculate_surcharge(
        "530", ctx(trade_type="exp", country=" be ", product_type="ftl"), conn)
    assert res["amount"] == 30


def test_specificity_order():
    s = specificity
    assert (s({"trade_type": "EXP", "product_type": "FTL", "country": "BE"})
            > s({"trade_type": "EXP", "country": "BE"})
            > s({"trade_type": "EXP", "product_type": "FTL"})
            > s({"trade_type": "EXP"})
            > s({}))


def test_select_rate_pure():
    rates = [
        {"id": 1, "cost_type": "revenue", "trade_type": "EXP", "country": None,
         "valid_from": "2026-01-01", "valid_to": None},
        {"id": 2, "cost_type": "revenue", "trade_type": "EXP", "country": "BE",
         "valid_from": "2026-01-01", "valid_to": None},
    ]
    assert select_rate(rates, ctx(trade_type="EXP", country="BE"))["id"] == 2
    assert select_rate(rates, ctx(trade_type="IMP", country="BE")) is None


# ── Voimassaolo ───────────────────────────────────────────────────────

@pytest.fixture
def dated(conn):
    add_rate(conn, rate=120, valid_from="2025-01-01", valid_to="2025-12-31")
    add_rate(conn, rate=150, valid_from="2026-01-01", valid_to="2026-06-30")
    add_rate(conn, rate=170, valid_from="2026-07-01", valid_to=None)
    return conn


@pytest.mark.parametrize("day, expected", [
    ("2025-01-01", 120),   # ensimmäinen päivä
    ("2025-12-31", 120),   # viimeinen päivä
    ("2026-01-01", 150),
    ("2026-06-30", 150),
    ("2026-07-01", 170),
    ("2030-01-01", 170),   # avoin valid_to
])
def test_rate_selected_by_date(dated, day, expected):
    assert calculate_surcharge("530", ctx(date=day), dated)["amount"] == expected


def test_no_rate_before_first_valid_from(dated):
    assert calculate_surcharge("530", ctx(date="2024-12-31"), dated) is None


def test_expired_rate_not_used(conn):
    add_rate(conn, valid_from="2025-01-01", valid_to="2025-12-31")
    assert calculate_surcharge("530", ctx(date="2026-01-01"), conn) is None


def test_date_object_accepted(dated):
    assert calculate_surcharge("530", ctx(date=date(2025, 6, 1)), dated)["amount"] == 120


def test_expired_specific_falls_back_to_general(conn):
    add_rate(conn, country="BE", rate=20, valid_to="2026-03-31")
    add_rate(conn, rate=10)
    assert calculate_surcharge("530", ctx(country="BE", date="2026-03-31"), conn)["amount"] == 20
    assert calculate_surcharge("530", ctx(country="BE", date="2026-04-01"), conn)["amount"] == 10


# ── Demodata ──────────────────────────────────────────────────────────

@pytest.fixture
def demo(conn):
    run_surcharges_migration(conn)
    return conn


def test_demo_seed_is_idempotent(demo):
    assert run_surcharges_migration(demo) == 0
    count = demo.execute("SELECT COUNT(*) FROM surcharge_rates").fetchone()[0]
    assert count == len(DEMO_SURCHARGE_RATES)


def test_demo_has_no_fuel_surcharge(demo):
    # Polttoainelisä (200) ei ole demodatassa: se siirretään fuel_rates-
    # taulusta (migrate_fuel_rates, test_fuel_migration.py).
    assert demo.execute(
        "SELECT COUNT(*) FROM surcharge_rates WHERE service_code = '200'"
    ).fetchone()[0] == 0


def test_demo_spec_example_fi_be_ftl(demo):
    """Luku 16: FI → BE FTL, rahti 2 000 €."""
    sale = ctx(trade_type=derive_trade_type("FI", "BE"), product_type="FTL",
               country="BE", freight_amount=2000, chargeable_weight=22000)
    assert calculate_surcharge("230", sale, demo)["amount"] == 180.00
    assert calculate_surcharge("530", sale, demo)["amount"] == 150.00
    cost = ctx(cost_type="cost", operator="Demo Ferries", product_type="FTL")
    assert calculate_surcharge("530", cost, demo)["amount"] == 180.00
    assert calculate_surcharge("520", cost, demo)["amount"] == 300.00


def test_demo_mobility_package_import(demo):
    res = calculate_surcharge(
        "230", ctx(trade_type=derive_trade_type("DE", "FI"), country="DE",
                   freight_amount=1000), demo)
    assert res["amount"] == 80.00
    # CROSS-liikenteelle ei ole liikkuvuuspakettihintaa
    assert calculate_surcharge(
        "230", ctx(trade_type="CROSS", country="DE", freight_amount=1000), demo) is None


def test_demo_marpol_ftl_and_ltl(demo):
    assert calculate_surcharge("540", ctx(product_type="FTL"), demo)["amount"] == 45.00
    ltl = calculate_surcharge("540", ctx(product_type="LTL", chargeable_weight=4000), demo)
    assert ltl["amount"] == 16.00
    small = calculate_surcharge("540", ctx(product_type="LTL", chargeable_weight=300), demo)
    assert small["amount"] == 5.00 and small["capped"] == "min"


def test_demo_baf_ltl_min(demo):
    res = calculate_surcharge(
        "520", ctx(cost_type="cost", operator="Demo Ferries", product_type="LTL",
                   chargeable_weight=1000), demo)
    assert res["amount"] == 15.00 and res["capped"] == "min"


def test_demo_ets_price_by_date(demo):
    assert calculate_surcharge("530", ctx(date="2025-11-01"), demo)["amount"] == 120.00
    assert calculate_surcharge("530", ctx(date="2026-02-01"), demo)["amount"] == 150.00


# ── API (CRUD) ────────────────────────────────────────────────────────

def payload(**kw):
    data = {
        "service_code": "530", "cost_type": "cost", "operator": "Baltic Demo Line",
        "rate_type": "fixed", "rate": 175, "valid_from": "2026-01-01",
    }
    data.update(kw)
    return data


def test_api_get_lists_demo_rates(client):
    c, _ = client
    res = c.get("/api/surcharge-rates")
    assert res.status_code == 200
    assert len(res.get_json()) == len(DEMO_SURCHARGE_RATES)


def test_api_get_filters(client):
    c, _ = client
    rows = c.get("/api/surcharge-rates?service=230&country=be").get_json()
    assert rows and all(r["service_code"] == "230" and r["country"] == "BE" for r in rows)
    rows = c.get("/api/surcharge-rates?service=530&date=2025-06-01").get_json()
    assert [r["rate"] for r in rows] == [120]
    rows = c.get("/api/surcharge-rates?service=530&cost_type=cost").get_json()
    assert [r["rate"] for r in rows] == [180]


def test_api_create(client):
    c, _ = client
    res = c.post("/api/surcharge-rates", json=payload(country="be", trade_type="exp"))
    assert res.status_code == 201
    row = res.get_json()
    assert row["id"] and row["rate"] == 175
    assert row["country"] == "BE" and row["trade_type"] == "EXP"
    assert row["valid_to"] is None


@pytest.mark.parametrize("override, fragment", [
    ({"service_code": "999"}, "palvelukoodi"),
    ({"service_code": None}, "service_code"),
    ({"cost_type": None}, "cost_type"),
    ({"cost_type": "both"}, "cost_type"),
    ({"rate_type": "per_pallet"}, "rate_type"),
    ({"trade_type": "XXX"}, "trade_type"),
    ({"product_type": "PTL"}, "product_type"),
    ({"rate": -1}, "negatiivinen"),
    ({"rate": None}, "rate"),
    ({"rate": "abc"}, "numero"),
    ({"min_amount": 50, "max_amount": 10}, "min_amount"),
    ({"valid_from": None}, "valid_from"),
    ({"valid_from": "2026-13-01"}, "valid_from"),
    ({"valid_to": "2025-12-31"}, "valid_to"),
])
def test_api_create_validation(client, override, fragment):
    c, _ = client
    res = c.post("/api/surcharge-rates", json=payload(**override))
    assert res.status_code == 400
    assert fragment in res.get_json()["error"]


def test_api_create_overlap_conflict(client):
    c, _ = client
    # Demodatassa: 530 cost Demo Ferries 2026-01-01 →
    res = c.post("/api/surcharge-rates",
                 json=payload(operator="Demo Ferries", valid_from="2026-05-01"))
    assert res.status_code == 409
    assert res.get_json()["conflict_id"]


def test_api_overlap_requires_same_targeting(client):
    c, _ = client
    # Sama koodi ja kausi, mutta eri cost_type → ei päällekkäisyyttä
    assert c.post("/api/surcharge-rates", json=payload(
        operator="Demo Ferries", cost_type="revenue", rate=170)).status_code == 201
    # Eri tuotetyyppi → ei päällekkäisyyttä
    assert c.post("/api/surcharge-rates", json=payload(
        operator="Demo Ferries", product_type="LTL")).status_code == 201


def test_api_adjacent_periods_allowed(client):
    c, _ = client
    first = payload(valid_from="2027-01-01", valid_to="2027-06-30")
    second = payload(valid_from="2027-07-01")
    assert c.post("/api/surcharge-rates", json=first).status_code == 201
    assert c.post("/api/surcharge-rates", json=second).status_code == 201
    overlapping = payload(valid_from="2026-12-01", valid_to="2027-01-01")
    assert c.post("/api/surcharge-rates", json=overlapping).status_code == 409


def test_api_open_ended_overlap(client):
    c, _ = client
    assert c.post("/api/surcharge-rates", json=payload(valid_from="2027-01-01")).status_code == 201
    # Avoin kausi alkaen aiemmin leikkaa avointa kautta
    assert c.post("/api/surcharge-rates",
                  json=payload(valid_from="2026-06-01", valid_to=None)).status_code == 409


def test_api_update(client):
    c, _ = client
    rid = c.post("/api/surcharge-rates", json=payload()).get_json()["id"]
    res = c.put(f"/api/surcharge-rates/{rid}", json=payload(rate=190, max_amount=200))
    assert res.status_code == 200
    assert res.get_json()["rate"] == 190 and res.get_json()["max_amount"] == 200


def test_api_update_does_not_conflict_with_itself(client):
    c, _ = client
    rid = c.post("/api/surcharge-rates", json=payload()).get_json()["id"]
    assert c.put(f"/api/surcharge-rates/{rid}",
                 json=payload(valid_from="2026-02-01")).status_code == 200


def test_api_update_overlap_conflict(client):
    c, _ = client
    rid = c.post("/api/surcharge-rates", json=payload()).get_json()["id"]
    res = c.put(f"/api/surcharge-rates/{rid}", json=payload(operator="Demo Ferries"))
    assert res.status_code == 409


def test_api_update_validation_and_404(client):
    c, _ = client
    rid = c.post("/api/surcharge-rates", json=payload()).get_json()["id"]
    assert c.put(f"/api/surcharge-rates/{rid}", json=payload(rate_type="x")).status_code == 400
    assert c.put("/api/surcharge-rates/99999", json=payload()).status_code == 404


def test_api_delete(client):
    c, _ = client
    rid = c.post("/api/surcharge-rates", json=payload()).get_json()["id"]
    assert c.delete(f"/api/surcharge-rates/{rid}").status_code == 200
    assert c.delete(f"/api/surcharge-rates/{rid}").status_code == 404
    ids = [r["id"] for r in c.get("/api/surcharge-rates").get_json()]
    assert rid not in ids


def test_api_created_rate_used_in_calculation(client):
    import app as flask_app
    c, _ = client
    c.post("/api/surcharge-rates", json=payload(
        operator="Baltic Demo Line", rate=175))
    conn = flask_app.get_db_connection()
    try:
        res = calculate_surcharge(
            "530", {"cost_type": "cost", "date": DAY,
                    "operator": "Baltic Demo Line"}, conn)
    finally:
        conn.close()
    assert res["amount"] == 175.00

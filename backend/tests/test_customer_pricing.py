"""Asiakashinnasto ja lisäsäännöt (spec luku 8, issue #5)."""

import sqlite3

import pytest

from customer_pricing import (
    find_rate_card, get_billing_rule, seed_customer_pricing,
    ensure_customer_pricing_tables, normalize_zip,
    insert_billing_rule, insert_rate_card,
    DEMO_PRICING_CUSTOMERS, DEMO_RATE_CARDS, DEMO_BILLING_RULES,
)


# ── Apufunktiot ───────────────────────────────────────────────────────

def _conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _customer_id(conn, name):
    return conn.execute("SELECT id FROM customers WHERE name = ?", (name,)).fetchone()[0]


def _new_customer(conn, name="Testi Demo Oy"):
    cur = conn.execute("INSERT INTO customers (name, country) VALUES (?, 'FI')", (name,))
    conn.commit()
    return cur.lastrowid


def _card(conn, cid, origin, dest, price, product="FTL",
          o_zip=None, d_zip=None, valid_from="2026-01-01", valid_to=None):
    rid = insert_rate_card(conn, {
        "customer_id": cid, "origin_country": origin, "origin_zip_prefix": o_zip,
        "dest_country": dest, "dest_zip_prefix": d_zip, "product_type": product,
        "freight_price": price, "valid_from": valid_from, "valid_to": valid_to,
    })
    conn.commit()
    return rid


def _rule(conn, cid, code, billed=1, rate_type=None, rate=None,
          valid_from="2026-01-01", valid_to=None):
    rid = insert_billing_rule(conn, {
        "customer_id": cid, "service_code": code, "billed": billed,
        "rate_type": rate_type, "rate": rate,
        "valid_from": valid_from, "valid_to": valid_to,
    })
    conn.commit()
    return rid


@pytest.fixture
def db(client):
    """Tyhjä skeema + demohinnasto; palauttaa (conn, uusi testiasiakas)."""
    _, db_path = client
    conn = _conn(db_path)
    cid = _new_customer(conn)
    yield conn, cid
    conn.close()


# ── find_rate_card: haku postinumeroalueella ──────────────────────────

class TestRateCardZipLookup:
    def test_zip_area_wins_over_country(self, db):
        conn, cid = db
        _card(conn, cid, "FI", "EE", 900)
        zip_id = _card(conn, cid, "FI", "EE", 980, o_zip="33")
        card = find_rate_card(conn, cid, {"country": "FI", "zip": "33100"},
                              "EE", "FTL", "2026-03-01")
        assert card["id"] == zip_id
        assert card["freight_price"] == 980

    def test_zip_outside_area_falls_back_to_country(self, db):
        conn, cid = db
        country_id = _card(conn, cid, "FI", "EE", 900)
        _card(conn, cid, "FI", "EE", 980, o_zip="33")
        card = find_rate_card(conn, cid, {"country": "FI", "zip": "00510"},
                              "EE", "FTL", "2026-03-01")
        assert card["id"] == country_id

    def test_zip_area_card_needs_zip(self, db):
        conn, cid = db
        _card(conn, cid, "FI", "EE", 980, o_zip="33")
        assert find_rate_card(conn, cid, "FI", "EE", "FTL", "2026-03-01") is None

    def test_longer_prefix_wins(self, db):
        conn, cid = db
        _card(conn, cid, "FI", "EE", 980, o_zip="33")
        long_id = _card(conn, cid, "FI", "EE", 1010, o_zip="331")
        card = find_rate_card(conn, cid, {"country": "FI", "zip": "33100"},
                              "EE", "FTL", "2026-03-01")
        assert card["id"] == long_id

    def test_both_ends_zip_wins_over_one_end(self, db):
        conn, cid = db
        _card(conn, cid, "FI", "LV", 1200, o_zip="3301")  # pitkä, vain toinen pää
        both = _card(conn, cid, "FI", "LV", 1300, o_zip="3", d_zip="1")
        card = find_rate_card(conn, cid, {"country": "FI", "zip": "33010"},
                              {"country": "LV", "zip": "LV-1010"}, "FTL", "2026-03-01")
        assert card["id"] == both

    def test_dest_zip_area(self, db):
        conn, cid = db
        _card(conn, cid, "FI", "LV", 1200)
        riga = _card(conn, cid, "FI", "LV", 1250, d_zip="10")
        card = find_rate_card(conn, cid, "FI", {"country": "LV", "zip": "LV-1050"},
                              "FTL", "2026-03-01")
        assert card["id"] == riga

    def test_zip_normalization(self):
        assert normalize_zip(" 1012 ab ") == "1012AB"
        assert normalize_zip("LV-1050") == "LV1050"
        assert normalize_zip("LV-1050", "LV") == "1050"
        assert normalize_zip("1050", "LV") == "1050"
        assert normalize_zip("EH1 1AA", "GB") == "EH11AA"  # ei maakoodia alussa
        assert normalize_zip("") is None


# ── find_rate_card: haku maalla ja ei osumaa ──────────────────────────

class TestRateCardCountryLookup:
    def test_country_match(self, db):
        conn, cid = db
        card_id = _card(conn, cid, "FI", "BE", 2000)
        card = find_rate_card(conn, cid, "fi", {"country": "be"}, "ftl", "2026-03-01")
        assert card["id"] == card_id
        assert card["freight_price"] == 2000

    def test_product_type_separates(self, db):
        conn, cid = db
        _card(conn, cid, "FI", "BE", 2000, product="FTL")
        ltl = _card(conn, cid, "FI", "BE", 650, product="LTL")
        assert find_rate_card(conn, cid, "FI", "BE", "LTL", "2026-03-01")["id"] == ltl

    @pytest.mark.parametrize("origin,dest,product", [
        ("FI", "NL", "FTL"),   # väärä kohdemaa
        ("SE", "BE", "FTL"),   # väärä lähtömaa
        ("BE", "FI", "FTL"),   # vastakkainen suunta
        ("FI", "BE", "LTL"),   # väärä tuote
    ])
    def test_no_match(self, db, origin, dest, product):
        conn, cid = db
        _card(conn, cid, "FI", "BE", 2000)
        assert find_rate_card(conn, cid, origin, dest, product, "2026-03-01") is None

    def test_other_customers_card_not_used(self, db):
        conn, cid = db
        other = _new_customer(conn, "Toinen Demo Oy")
        _card(conn, other, "FI", "BE", 2000)
        assert find_rate_card(conn, cid, "FI", "BE", "FTL", "2026-03-01") is None

    @pytest.mark.parametrize("kwargs", [
        {"customer_id": None},
        {"origin": None},
        {"dest": {"zip": "1000"}},
        {"product_type": "XL"},
        {"date": None},
        {"date": "2026-13-01"},
    ])
    def test_missing_input_raises(self, db, kwargs):
        conn, cid = db
        args = {"customer_id": cid, "origin": "FI", "dest": "BE",
                "product_type": "FTL", "date": "2026-03-01", **kwargs}
        with pytest.raises(ValueError):
            find_rate_card(conn, **args)


# ── find_rate_card: voimassaolo ───────────────────────────────────────

class TestRateCardValidity:
    def test_before_valid_from(self, db):
        conn, cid = db
        _card(conn, cid, "FI", "BE", 2000, valid_from="2026-02-01")
        assert find_rate_card(conn, cid, "FI", "BE", "FTL", "2026-01-31") is None

    def test_boundaries_inclusive(self, db):
        conn, cid = db
        _card(conn, cid, "FI", "BE", 2000, valid_from="2026-02-01", valid_to="2026-02-28")
        assert find_rate_card(conn, cid, "FI", "BE", "FTL", "2026-02-01")
        assert find_rate_card(conn, cid, "FI", "BE", "FTL", "2026-02-28")
        assert find_rate_card(conn, cid, "FI", "BE", "FTL", "2026-03-01") is None

    def test_price_change(self, db):
        conn, cid = db
        old = _card(conn, cid, "FI", "LT", 1400, valid_from="2025-01-01",
                    valid_to="2025-12-31")
        new = _card(conn, cid, "FI", "LT", 1450, valid_from="2026-01-01")
        assert find_rate_card(conn, cid, "FI", "LT", "FTL", "2025-12-31")["id"] == old
        assert find_rate_card(conn, cid, "FI", "LT", "FTL", "2026-01-01")["id"] == new

    def test_expired_zip_card_falls_back_to_country(self, db):
        conn, cid = db
        country = _card(conn, cid, "FI", "EE", 900)
        _card(conn, cid, "FI", "EE", 980, o_zip="33", valid_to="2026-01-31")
        card = find_rate_card(conn, cid, {"country": "FI", "zip": "33100"},
                              "EE", "FTL", "2026-03-01")
        assert card["id"] == country


# ── get_billing_rule ──────────────────────────────────────────────────

class TestBillingRule:
    def test_own_price(self, db):
        conn, cid = db
        rid = _rule(conn, cid, "200", rate_type="percent", rate=25)
        rule = get_billing_rule(conn, cid, "200", "2026-03-01")
        assert rule["id"] == rid
        assert rule["billed"] is True
        assert rule["rate_type"] == "percent"
        assert rule["rate"] == 25

    def test_billed_false(self, db):
        conn, cid = db
        _rule(conn, cid, "230", billed=0)
        rule = get_billing_rule(conn, cid, "230", "2026-03-01")
        assert rule["billed"] is False
        assert rule["rate_type"] is None and rule["rate"] is None

    def test_billed_with_list_price(self, db):
        conn, cid = db
        _rule(conn, cid, "530")
        rule = get_billing_rule(conn, cid, "530", "2026-03-01")
        assert rule["billed"] is True
        assert rule["rate_type"] is None

    def test_pass_through(self, db):
        conn, cid = db
        _rule(conn, cid, "510", rate_type="pass_through", rate=5)
        rule = get_billing_rule(conn, cid, "510", "2026-03-01")
        assert rule["rate_type"] == "pass_through" and rule["rate"] == 5

    def test_no_rule_returns_none(self, db):
        conn, cid = db
        _rule(conn, cid, "200", rate_type="percent", rate=25)
        assert get_billing_rule(conn, cid, "530", "2026-03-01") is None
        other = _new_customer(conn, "Toinen Demo Oy")
        assert get_billing_rule(conn, other, "200", "2026-03-01") is None

    def test_validity(self, db):
        conn, cid = db
        old = _rule(conn, cid, "200", rate_type="percent", rate=20,
                    valid_from="2025-01-01", valid_to="2025-12-31")
        new = _rule(conn, cid, "200", rate_type="percent", rate=25,
                    valid_from="2026-01-01", valid_to="2026-06-30")
        assert get_billing_rule(conn, cid, "200", "2024-12-31") is None
        assert get_billing_rule(conn, cid, "200", "2025-12-31")["id"] == old
        assert get_billing_rule(conn, cid, "200", "2026-01-01")["id"] == new
        assert get_billing_rule(conn, cid, "200", "2026-07-01") is None

    def test_missing_input_raises(self, db):
        conn, cid = db
        with pytest.raises(ValueError):
            get_billing_rule(conn, cid, "", "2026-03-01")
        with pytest.raises(ValueError):
            get_billing_rule(conn, None, "200", "2026-03-01")
        with pytest.raises(ValueError):
            get_billing_rule(conn, cid, "200", None)


# ── Demodata ──────────────────────────────────────────────────────────

class TestDemoData:
    def test_demo_customers_and_pricing(self, client):
        _, db_path = client
        conn = _conn(db_path)
        plastics = _customer_id(conn, "Nordic Demo Plastics Oy")
        baltic = _customer_id(conn, "Baltic Demo Trading Oy")

        # Luku 17: FI → BE FTL 2 000 €, polttoainelisä 25 %, muut listahinnalla
        card = find_rate_card(conn, plastics, "FI", "BE", "FTL", "2026-03-01")
        assert card["freight_price"] == 2000
        fuel = get_billing_rule(conn, plastics, "200", "2026-03-01")
        assert fuel["rate_type"] == "percent" and fuel["rate"] == 25
        assert get_billing_rule(conn, plastics, "230", "2026-03-01") is None
        assert get_billing_rule(conn, plastics, "530", "2026-03-01") is None

        # Luku 8.2: liikkuvuuspakettia ei laskuteta, satamamaksu läpilaskutetaan
        assert get_billing_rule(conn, baltic, "230", "2026-03-01")["billed"] is False
        port = get_billing_rule(conn, baltic, "510", "2026-03-01")
        assert port["rate_type"] == "pass_through" and port["rate"] == 5
        tampere = find_rate_card(conn, baltic, {"country": "FI", "zip": "33100"},
                                 "EE", "FTL", "2026-03-01")
        helsinki = find_rate_card(conn, baltic, {"country": "FI", "zip": "00510"},
                                  "EE", "FTL", "2026-03-01")
        assert tampere["freight_price"] == 980
        assert helsinki["freight_price"] == 900
        conn.close()

    def test_seed_counts_and_idempotent(self, client):
        _, db_path = client
        conn = _conn(db_path)
        n_cards = conn.execute("SELECT COUNT(*) FROM customer_rate_cards").fetchone()[0]
        n_rules = conn.execute("SELECT COUNT(*) FROM customer_billing_rules").fetchone()[0]
        assert n_cards == sum(len(v) for v in DEMO_RATE_CARDS.values())
        assert n_rules == sum(len(v) for v in DEMO_BILLING_RULES.values())
        assert seed_customer_pricing(conn) == (0, 0)
        ensure_customer_pricing_tables(conn)
        for customer in DEMO_PRICING_CUSTOMERS:
            assert conn.execute(
                "SELECT COUNT(*) FROM customers WHERE name = ?", (customer[0],)
            ).fetchone()[0] == 1
        conn.close()

    def test_existing_demo_customer_is_reused(self, tmp_path):
        from init_db import create_schema
        conn = _conn(str(tmp_path / "seed.db"))
        create_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS services (code TEXT PRIMARY KEY)")
        existing = conn.execute(
            "INSERT INTO customers (name, country) VALUES ('Nordic Demo Plastics Oy', 'FI')"
        ).lastrowid
        ensure_customer_pricing_tables(conn)
        seed_customer_pricing(conn)
        assert conn.execute(
            "SELECT COUNT(*) FROM customers WHERE name = 'Nordic Demo Plastics Oy'"
        ).fetchone()[0] == 1
        assert find_rate_card(conn, existing, "FI", "BE", "FTL", "2026-03-01")
        conn.close()

    def test_seed_skipped_when_tables_have_rows(self, client):
        c, db_path = client
        conn = _conn(db_path)
        conn.execute("DELETE FROM customer_billing_rules")
        conn.commit()
        assert seed_customer_pricing(conn) == (0, 0)  # hinnastossa yhä rivejä
        conn.close()


# ── API: hinnasto ─────────────────────────────────────────────────────

RATE_CARD = {
    "origin_country": "fi", "origin_zip_prefix": "33",
    "dest_country": "nl", "product_type": "ftl",
    "freight_price": 1900, "valid_from": "2026-01-01",
}


@pytest.fixture
def api(client):
    c, db_path = client
    conn = _conn(db_path)
    cid = _new_customer(conn)
    conn.close()
    return c, cid, db_path


class TestRateCardApi:
    def test_create_list_update_delete(self, api):
        c, cid, _ = api
        r = c.post(f"/api/customers/{cid}/rate-cards", json=RATE_CARD)
        assert r.status_code == 201
        card = r.get_json()
        assert card["customer_id"] == cid
        assert card["origin_country"] == "FI" and card["dest_country"] == "NL"
        assert card["product_type"] == "FTL" and card["origin_zip_prefix"] == "33"
        assert card["dest_zip_prefix"] is None and card["valid_to"] is None

        listed = c.get(f"/api/customers/{cid}/rate-cards").get_json()
        assert [x["id"] for x in listed] == [card["id"]]

        r = c.put(f"/api/rate-cards/{card['id']}",
                  json={**RATE_CARD, "freight_price": 1950, "valid_to": "2026-12-31"})
        assert r.status_code == 200
        assert r.get_json()["freight_price"] == 1950
        assert r.get_json()["customer_id"] == cid

        assert c.delete(f"/api/rate-cards/{card['id']}").status_code == 200
        assert c.get(f"/api/customers/{cid}/rate-cards").get_json() == []
        assert c.delete(f"/api/rate-cards/{card['id']}").status_code == 404

    def test_list_date_filter(self, api):
        c, cid, _ = api
        c.post(f"/api/customers/{cid}/rate-cards",
               json={**RATE_CARD, "valid_from": "2025-01-01", "valid_to": "2025-12-31"})
        c.post(f"/api/customers/{cid}/rate-cards", json=RATE_CARD)
        rows = c.get(f"/api/customers/{cid}/rate-cards?date=2025-06-01").get_json()
        assert len(rows) == 1 and rows[0]["valid_from"] == "2025-01-01"

    def test_unknown_customer_and_row(self, api):
        c, _, _ = api
        assert c.get("/api/customers/9999/rate-cards").status_code == 404
        assert c.post("/api/customers/9999/rate-cards", json=RATE_CARD).status_code == 404
        assert c.put("/api/rate-cards/9999", json=RATE_CARD).status_code == 404

    @pytest.mark.parametrize("change", [
        {"origin_country": ""},
        {"dest_country": None},
        {"product_type": "XL"},
        {"freight_price": None},
        {"freight_price": "abc"},
        {"freight_price": -1},
        {"valid_from": ""},
        {"valid_to": "2025-12-31"},
        {"origin_zip_prefix": "33*"},
    ])
    def test_validation(self, api, change):
        c, cid, _ = api
        r = c.post(f"/api/customers/{cid}/rate-cards", json={**RATE_CARD, **change})
        assert r.status_code == 400
        assert r.get_json()["errors"]

    def test_overlap_conflict(self, api):
        c, cid, _ = api
        first = c.post(f"/api/customers/{cid}/rate-cards", json=RATE_CARD).get_json()
        r = c.post(f"/api/customers/{cid}/rate-cards",
                   json={**RATE_CARD, "valid_from": "2026-06-01"})
        assert r.status_code == 409
        assert r.get_json()["conflict_id"] == first["id"]

    def test_different_targeting_no_conflict(self, api):
        c, cid, _ = api
        c.post(f"/api/customers/{cid}/rate-cards", json=RATE_CARD)
        for change in ({"origin_zip_prefix": None}, {"origin_zip_prefix": "331"},
                       {"product_type": "LTL"}, {"dest_zip_prefix": "10"}):
            r = c.post(f"/api/customers/{cid}/rate-cards", json={**RATE_CARD, **change})
            assert r.status_code == 201, change

    def test_zip_prefix_country_code_stripped(self, api):
        c, cid, _ = api
        r = c.post(f"/api/customers/{cid}/rate-cards", json={
            **RATE_CARD, "dest_country": "LV", "dest_zip_prefix": "LV-10"})
        assert r.status_code == 201
        assert r.get_json()["dest_zip_prefix"] == "10"

    def test_consecutive_periods_and_update_self(self, api):
        c, cid, _ = api
        first = c.post(f"/api/customers/{cid}/rate-cards",
                       json={**RATE_CARD, "valid_to": "2026-06-30"}).get_json()
        r = c.post(f"/api/customers/{cid}/rate-cards",
                   json={**RATE_CARD, "valid_from": "2026-07-01"})
        assert r.status_code == 201
        # Oman rivin muokkaus ei törmää itseensä, mutta jatkaminen seuraavan päälle törmää
        assert c.put(f"/api/rate-cards/{first['id']}",
                     json={**RATE_CARD, "freight_price": 1, "valid_to": "2026-06-30"}
                     ).status_code == 200
        assert c.put(f"/api/rate-cards/{first['id']}",
                     json={**RATE_CARD, "valid_to": "2026-07-01"}).status_code == 409


# ── API: lisäsäännöt ──────────────────────────────────────────────────

class TestBillingRuleApi:
    def test_create_list_update_delete(self, api):
        c, cid, _ = api
        r = c.post(f"/api/customers/{cid}/billing-rules", json={
            "service_code": "200", "billed": True, "rate_type": "percent",
            "rate": 25, "valid_from": "2026-01-01",
        })
        assert r.status_code == 201
        rule = r.get_json()
        assert rule["billed"] is True and rule["rate"] == 25

        r = c.put(f"/api/billing-rules/{rule['id']}", json={
            "service_code": "200", "billed": "false", "valid_from": "2026-01-01",
        })
        assert r.status_code == 200
        assert r.get_json()["billed"] is False
        assert r.get_json()["rate_type"] is None

        listed = c.get(f"/api/customers/{cid}/billing-rules").get_json()
        assert [x["id"] for x in listed] == [rule["id"]]
        assert listed[0]["billed"] is False

        assert c.delete(f"/api/billing-rules/{rule['id']}").status_code == 200
        assert c.delete(f"/api/billing-rules/{rule['id']}").status_code == 404

    def test_billed_defaults_true_and_list_price(self, api):
        c, cid, _ = api
        r = c.post(f"/api/customers/{cid}/billing-rules",
                   json={"service_code": "530", "valid_from": "2026-01-01"})
        assert r.status_code == 201
        assert r.get_json()["billed"] is True
        assert r.get_json()["rate_type"] is None

    def test_pass_through_without_margin(self, api):
        c, cid, _ = api
        r = c.post(f"/api/customers/{cid}/billing-rules", json={
            "service_code": "510", "rate_type": "pass_through",
            "valid_from": "2026-01-01",
        })
        assert r.status_code == 201
        assert r.get_json()["rate"] is None

    @pytest.mark.parametrize("payload", [
        {"service_code": "999"},                                     # tuntematon koodi
        {"service_code": ""},
        {"service_code": "200", "rate_type": "bogus", "rate": 1},
        {"service_code": "200", "rate_type": "percent"},             # rate puuttuu
        {"service_code": "200", "rate": 25},                         # rate_type puuttuu
        {"service_code": "200", "rate_type": "percent", "rate": -5},
        {"service_code": "230", "billed": False, "rate_type": "percent", "rate": 9},
        {"service_code": "230", "billed": "maybe"},
        {"service_code": "200", "valid_from": "2026-02-01", "valid_to": "2026-01-01"},
    ])
    def test_validation(self, api, payload):
        c, cid, _ = api
        payload = {"valid_from": "2026-01-01", **payload}
        r = c.post(f"/api/customers/{cid}/billing-rules", json=payload)
        assert r.status_code == 400, payload

    def test_overlap_conflict(self, api):
        c, cid, _ = api
        rule = {"service_code": "200", "rate_type": "percent", "rate": 25,
                "valid_from": "2026-01-01", "valid_to": "2026-12-31"}
        first = c.post(f"/api/customers/{cid}/billing-rules", json=rule).get_json()
        r = c.post(f"/api/customers/{cid}/billing-rules",
                   json={**rule, "valid_from": "2026-12-31", "valid_to": None})
        assert r.status_code == 409
        assert r.get_json()["conflict_id"] == first["id"]
        r = c.post(f"/api/customers/{cid}/billing-rules",
                   json={**rule, "valid_from": "2027-01-01", "valid_to": None})
        assert r.status_code == 201
        # Eri palvelukoodi ei törmää
        r = c.post(f"/api/customers/{cid}/billing-rules",
                   json={**rule, "service_code": "230"})
        assert r.status_code == 201

    def test_unknown_customer_and_row(self, api):
        c, _, _ = api
        rule = {"service_code": "200", "valid_from": "2026-01-01"}
        assert c.get("/api/customers/9999/billing-rules").status_code == 404
        assert c.post("/api/customers/9999/billing-rules", json=rule).status_code == 404
        assert c.put("/api/billing-rules/9999", json=rule).status_code == 404


# ── Asiakkaan poisto ──────────────────────────────────────────────────

def test_customer_delete_removes_pricing(api):
    c, cid, db_path = api
    c.post(f"/api/customers/{cid}/rate-cards", json=RATE_CARD)
    c.post(f"/api/customers/{cid}/billing-rules",
           json={"service_code": "230", "billed": False, "valid_from": "2026-01-01"})
    assert c.delete(f"/api/customers/{cid}").status_code == 200
    conn = _conn(db_path)
    for table in ("customer_rate_cards", "customer_billing_rules"):
        assert conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE customer_id = ?", (cid,)
        ).fetchone()[0] == 0
    # Muiden asiakkaiden (demo) rivit säilyvät
    assert conn.execute("SELECT COUNT(*) FROM customer_rate_cards").fetchone()[0] > 0
    conn.close()

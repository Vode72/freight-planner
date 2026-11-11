"""Vetäjärekisteri (tractors): endpointit, carrier-validointi, pikaluonti,
kaluston yhteiset ominaisuudet (vetäjät + trailerit)."""
import sqlite3

import pytest

import equipment

FEATURES_OFF = {key: False for key in equipment.FEATURE_KEYS}


# ── Apurit ────────────────────────────────────────────────────────────

def _carrier(c, name="Demo Testikuljetus Oy"):
    resp = c.post("/api/carriers", json={"name": name, "country": "FI", "city": "Demola"})
    assert resp.status_code == 201
    return resp.get_json()["id"]


def _create_tractor(c, carrier_id, reg="TST-001", vehicle_type="vetoauto", **extra):
    return c.post("/api/tractors", json={
        "registration_number": reg, "carrier_id": carrier_id,
        "vehicle_type": vehicle_type, **extra,
    })


def _tractor(c, carrier_id, reg="TST-001", vehicle_type="vetoauto", **extra):
    resp = _create_tractor(c, carrier_id, reg, vehicle_type, **extra)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["tractor"]


def _trip_payload(**data):
    return {"first_pickup_country": "FI", "trip_end_country": "DE",
            "loading_date": "2026-11-20", "delivery_date": "2026-11-22", **data}


def _create_trip(c, **data):
    return c.post("/api/trips", json=_trip_payload(**data))


def _trip(c, trip_id):
    return c.get(f"/api/trips/{trip_id}").get_json()


def _set_trip_status(db_path, trip_id, status):
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE trips SET status = ? WHERE id = ?", (status, trip_id))
    conn.commit()
    conn.close()


@pytest.fixture
def carriers(client):
    c, db_path = client
    return c, db_path, _carrier(c, "Demo Alfa Oy"), _carrier(c, "Demo Beta Oy")


# ── Luonti, haku, pikaluonti ──────────────────────────────────────────

def test_quick_create_returns_full_row_with_defaults(carriers):
    c, _, alfa, _ = carriers
    resp = _create_tractor(c, alfa, "  abc-123 ")
    assert resp.status_code == 201
    body = resp.get_json()
    tractor = body["tractor"]
    assert body["id"] == tractor["id"]
    assert tractor["registration_number"] == "ABC-123"
    assert tractor["carrier_id"] == alfa
    assert tractor["carrier_name"] == "Demo Alfa Oy"
    assert tractor["vehicle_type"] == "vetoauto"
    assert tractor["status"] == "aktiivinen"
    assert tractor["features"] == FEATURES_OFF
    assert tractor["max_weight"] is None and tractor["max_ldm"] is None
    assert tractor["make_model"] is None and tractor["emission_class"] is None
    # Feature-sarakkeet eivät vuoda rivin juureen
    assert not set(equipment.FEATURE_KEYS) & set(tractor)


def test_create_truck_with_capacity_and_features(carriers):
    c, _, alfa, _ = carriers
    tractor = _tractor(c, alfa, "KAA-100", "kuorma-auto",
                       make_model="Demo City 260", emission_class="EURO VI",
                       max_weight="8000", max_ldm="7,2", max_volume=45,
                       features={"tail_lift": True, "temperature_controlled": 1},
                       notes="Demo")
    assert tractor["max_weight"] == 8000
    assert tractor["max_ldm"] == 7.2
    assert tractor["max_volume"] == 45
    assert tractor["features"] == FEATURES_OFF | {"tail_lift": True,
                                                  "temperature_controlled": True}
    assert c.get(f"/api/tractors/{tractor['id']}").get_json() == tractor


def test_get_tractor_404(client):
    c, _ = client
    assert c.get("/api/tractors/999").status_code == 404


@pytest.mark.parametrize("missing", ["registration_number", "carrier_id", "vehicle_type"])
def test_required_fields(carriers, missing):
    c, _, alfa, _ = carriers
    payload = {"registration_number": "REQ-001", "carrier_id": alfa, "vehicle_type": "vetoauto"}
    payload[missing] = "  " if missing == "registration_number" else None
    resp = c.post("/api/tractors", json=payload)
    assert resp.status_code == 400
    assert resp.get_json()["errors"]


@pytest.mark.parametrize("field,value", [
    ("vehicle_type", "pakettiauto"),
    ("status", "Vapaa"),
    ("emission_class", "EURO 9"),
    ("carrier_id", "abc"),
    ("features", ["adr"]),
    ("features", {"adr": "kyllä"}),
    ("features", {"lentokyky": True}),
])
def test_invalid_values(carriers, field, value):
    c, _, alfa, _ = carriers
    payload = {"registration_number": "BAD-001", "carrier_id": alfa,
               "vehicle_type": "vetoauto", field: value}
    resp = c.post("/api/tractors", json=payload)
    assert resp.status_code == 400, field


def test_unknown_carrier(client):
    c, _ = client
    resp = _create_tractor(c, 999)
    assert resp.status_code == 400
    assert "Kuljetusyhtiötä ei löydy" in resp.get_json()["error"]


def test_post_without_body(client):
    c, _ = client
    assert c.post("/api/tractors", data="x", content_type="text/plain").status_code == 400


def test_registration_is_unique_case_insensitive(carriers):
    c, _, alfa, beta = carriers
    first = _tractor(c, alfa, "Uni-001")
    for reg in ("UNI-001", "uni-001", " uni-001 "):
        resp = _create_tractor(c, beta, reg)
        assert resp.status_code == 409, reg
        body = resp.get_json()
        assert body["existing"]["id"] == first["id"]
        assert body["existing"]["carrier_name"] == "Demo Alfa Oy"
    assert len(c.get("/api/tractors").get_json()) == 1


def test_registration_unique_in_database(carriers):
    """UNIQUE COLLATE NOCASE estää tuplan myös ohi API:n."""
    c, db_path, alfa, _ = carriers
    _tractor(c, alfa, "DBU-001")
    conn = sqlite3.connect(db_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO tractors (registration_number, carrier_id) VALUES ('dbu-001', ?)",
                     (alfa,))
    conn.close()


def test_capacity_only_for_truck(carriers):
    c, _, alfa, _ = carriers
    resp = _create_tractor(c, alfa, "CAP-001", "vetoauto", max_weight=8000)
    assert resp.status_code == 400
    assert "kuorma-autolle" in resp.get_json()["error"]


@pytest.mark.parametrize("field,value", [
    ("max_weight", -1), ("max_weight", 0), ("max_weight", "7500,5"),
    ("max_ldm", "abc"), ("max_volume", True),
])
def test_capacity_validation(carriers, field, value):
    c, _, alfa, _ = carriers
    resp = _create_tractor(c, alfa, "CAP-002", "kuorma-auto", **{field: value})
    assert resp.status_code == 400, (field, value)


def test_database_checks(carriers):
    """CHECK-ehdot pitävät, vaikka API ohitettaisiin."""
    c, db_path, alfa, _ = carriers
    conn = sqlite3.connect(db_path)
    bad = [
        ("INSERT INTO tractors (registration_number, carrier_id, vehicle_type, max_weight) "
         "VALUES ('CHK-1', ?, 'vetoauto', 1000)"),
        "INSERT INTO tractors (registration_number, carrier_id, status) VALUES ('CHK-2', ?, 'Vapaa')",
        "INSERT INTO tractors (registration_number, carrier_id, crane) VALUES ('CHK-3', ?, 2)",
        "INSERT INTO tractors (registration_number, carrier_id) VALUES ('  ', ?)",
        "INSERT INTO trailers (plate_number, identifier, trailer_type, adr) VALUES ('X', 'X', 'Megatrailer', 5)",
    ]
    for sql in bad:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, (alfa,) if "?" in sql else ())
    conn.close()


def test_list_filters(carriers):
    c, _, alfa, beta = carriers
    _tractor(c, alfa, "AAA-001", make_model="Demo Hauler 500")
    _tractor(c, alfa, "AAA-101", "kuorma-auto")
    _tractor(c, beta, "BBB-001", status="huollossa")
    _tractor(c, beta, "BBB-002", status="poistettu")

    def regs(query=""):
        resp = c.get(f"/api/tractors{query}")
        assert resp.status_code == 200
        return sorted(t["registration_number"] for t in resp.get_json())

    assert regs() == ["AAA-001", "AAA-101", "BBB-001"]  # poistettu piilossa
    assert regs("?include_removed=1") == ["AAA-001", "AAA-101", "BBB-001", "BBB-002"]
    assert regs(f"?carrier_id={alfa}") == ["AAA-001", "AAA-101"]
    assert regs(f"?carrier_id={beta}") == ["BBB-001"]
    assert regs("?vehicle_type=kuorma-auto") == ["AAA-101"]
    assert regs("?status=poistettu") == ["BBB-002"]
    assert regs("?q=hauler") == ["AAA-001"]
    assert regs("?q=bbb") == ["BBB-001"]
    assert regs("?q=Beta") == ["BBB-001"]
    assert regs("?q=%25") == []  # LIKE-jokerit ovat kirjaimellisia


@pytest.mark.parametrize("query", ["carrier_id=x", "vehicle_type=bussi", "status=Vapaa"])
def test_list_invalid_filters(client, query):
    c, _ = client
    assert c.get(f"/api/tractors?{query}").status_code == 400


def test_equipment_meta(client):
    c, _ = client
    meta = c.get("/api/equipment-meta").get_json()
    assert [f["key"] for f in meta["features"]] == ["adr", "temperature_controlled",
                                                    "tail_lift", "crane"]
    assert meta["vehicle_types"] == ["vetoauto", "kuorma-auto"]
    assert meta["tractor_statuses"] == ["aktiivinen", "huollossa", "poistettu"]
    assert "EURO VI" in meta["emission_classes"]
    assert "Megatrailer" in meta["trailer_types"]


# ── Päivitys ja poisto ────────────────────────────────────────────────

def test_put_is_partial(carriers):
    c, _, alfa, _ = carriers
    tractor = _tractor(c, alfa, "PUT-001", make_model="Demo Hauler 460",
                       emission_class="EURO V", features={"adr": True})
    resp = c.put(f"/api/tractors/{tractor['id']}", json={"status": "huollossa"})
    assert resp.status_code == 200
    updated = resp.get_json()["tractor"]
    assert updated == tractor | {"status": "huollossa"}

    resp = c.put(f"/api/tractors/{tractor['id']}", json={"features": {"crane": True}})
    assert resp.get_json()["tractor"]["features"] == FEATURES_OFF | {"adr": True, "crane": True}


def test_put_validation_and_404(carriers):
    c, _, alfa, _ = carriers
    tractor = _tractor(c, alfa, "PUT-002")
    assert c.put("/api/tractors/999", json={"status": "huollossa"}).status_code == 404
    assert c.put(f"/api/tractors/{tractor['id']}", json={"status": "rikki"}).status_code == 400
    assert c.put(f"/api/tractors/{tractor['id']}",
                 json={"registration_number": ""}).status_code == 400
    assert c.put(f"/api/tractors/{tractor['id']}", json={"carrier_id": 999}).status_code == 400


def test_put_duplicate_registration(carriers):
    c, _, alfa, _ = carriers
    _tractor(c, alfa, "DUP-001")
    other = _tractor(c, alfa, "DUP-002")
    resp = c.put(f"/api/tractors/{other['id']}", json={"registration_number": "dup-001"})
    assert resp.status_code == 409
    # Oman rekisterin tallennus uudelleen (eri kirjainkoolla) on sallittu
    resp = c.put(f"/api/tractors/{other['id']}", json={"registration_number": "dup-002"})
    assert resp.status_code == 200


def test_truck_to_tractor_clears_capacity(carriers):
    c, _, alfa, _ = carriers
    truck = _tractor(c, alfa, "TYP-001", "kuorma-auto", max_weight=9000, max_ldm=7)
    resp = c.put(f"/api/tractors/{truck['id']}", json={"vehicle_type": "vetoauto"})
    assert resp.status_code == 200
    tractor = resp.get_json()["tractor"]
    assert (tractor["max_weight"], tractor["max_ldm"]) == (None, None)
    # Kapasiteetti eksplisiittisesti vetoautolle → virhe
    resp = c.put(f"/api/tractors/{truck['id']}", json={"max_weight": 9000})
    assert resp.status_code == 400


def test_delete_unused_tractor(carriers):
    c, _, alfa, _ = carriers
    tractor = _tractor(c, alfa, "DEL-001")
    assert c.delete(f"/api/tractors/{tractor['id']}").status_code == 200
    assert c.get(f"/api/tractors/{tractor['id']}").status_code == 404
    assert c.delete(f"/api/tractors/{tractor['id']}").status_code == 404


def test_delete_used_tractor_conflicts(carriers):
    c, db_path, alfa, _ = carriers
    tractor = _tractor(c, alfa, "DEL-002")
    trip_id = _create_trip(c, carrier_id=alfa, tractor_id=tractor["id"]).get_json()["id"]
    _set_trip_status(db_path, trip_id, "Laskutettu")  # myös historia estää poiston
    resp = c.delete(f"/api/tractors/{tractor['id']}")
    assert resp.status_code == 409
    assert resp.get_json()["trip_count"] == 1
    assert "poistettu" in resp.get_json()["error"]
    resp = c.put(f"/api/tractors/{tractor['id']}", json={"status": "poistettu"})
    assert resp.status_code == 200


# ── Carrier-validointi: tractor.carrier_id = trip.carrier_id ──────────

def test_trip_with_matching_tractor(carriers):
    c, _, alfa, _ = carriers
    tractor = _tractor(c, alfa, "TRP-T01", "kuorma-auto")
    resp = _create_trip(c, carrier_id=str(alfa), tractor_id=tractor["id"])
    assert resp.status_code == 201
    body = resp.get_json()
    assert (body["carrier_id"], body["tractor_id"], body["truck_plate"]) == (
        alfa, tractor["id"], "TRP-T01")
    trip = _trip(c, body["id"])
    assert trip["tractor_id"] == tractor["id"]
    assert trip["truck_plate"] == "TRP-T01"
    assert trip["tractor_registration"] == "TRP-T01"
    assert trip["tractor_vehicle_type"] == "kuorma-auto"
    listed = next(t for t in c.get("/api/trips").get_json() if t["id"] == body["id"])
    assert listed["tractor_registration"] == "TRP-T01"


def test_trip_post_rejects_other_carriers_tractor(carriers):
    c, _, alfa, beta = carriers
    tractor = _tractor(c, beta, "OTH-001")
    resp = _create_trip(c, carrier_id=alfa, tractor_id=tractor["id"])
    assert resp.status_code == 400
    assert "eri kuljetusyhtiölle" in resp.get_json()["error"]
    assert c.get("/api/trips").get_json() == []


def test_trip_put_rejects_other_carriers_tractor(carriers):
    c, _, alfa, beta = carriers
    own = _tractor(c, alfa, "PUT-T01")
    other = _tractor(c, beta, "PUT-T02")
    trip_id = _create_trip(c, carrier_id=alfa, tractor_id=own["id"]).get_json()["id"]
    resp = c.put(f"/api/trips/{trip_id}", json=_trip_payload(carrier_id=alfa, tractor_id=other["id"]))
    assert resp.status_code == 400
    # Carrierin vaihto ilman vetäjän vaihtoa → ristiriita
    resp = c.put(f"/api/trips/{trip_id}", json=_trip_payload(carrier_id=beta, tractor_id=own["id"]))
    assert resp.status_code == 400
    assert _trip(c, trip_id)["tractor_id"] == own["id"]
    # Molemmat vaihdetaan yhdessä → ok
    resp = c.put(f"/api/trips/{trip_id}", json=_trip_payload(carrier_id=beta, tractor_id=other["id"]))
    assert resp.status_code == 200
    trip = _trip(c, trip_id)
    assert (trip["carrier_id"], trip["tractor_id"], trip["truck_plate"]) == (
        beta, other["id"], "PUT-T02")


def test_trip_without_carrier_takes_tractors_carrier(carriers):
    c, _, alfa, beta = carriers
    tractor = _tractor(c, beta, "AUTO-01")
    resp = _create_trip(c, tractor_id=tractor["id"])  # ei carrieria
    assert resp.status_code == 201
    assert resp.get_json()["carrier_id"] == beta
    trip_id = resp.get_json()["id"]
    assert _trip(c, trip_id)["carrier_id"] == beta

    # PUT: carrier tyhjä, olemassa oleva vetäjä valitaan → carrier vetäjältä
    other_trip = _create_trip(c).get_json()["id"]
    resp = c.put(f"/api/trips/{other_trip}", json=_trip_payload(carrier_id="", tractor_id=tractor["id"]))
    assert resp.status_code == 200
    assert resp.get_json()["carrier_id"] == beta
    assert _trip(c, other_trip)["carrier_id"] == beta


def test_trip_without_tractor_is_allowed(carriers):
    c, _, alfa, _ = carriers
    resp = _create_trip(c, carrier_id=alfa)
    assert resp.status_code == 201
    trip = _trip(c, resp.get_json()["id"])
    assert trip["tractor_id"] is None and trip["truck_plate"] is None
    assert trip["trailer_id"] is None  # traileri on valinnainen


@pytest.mark.parametrize("tractor_id,carrier_id,message", [
    (999, None, "Vetäjää ei löydy"),
    ("abc", None, "tractor_id"),
    (None, "abc", "carrier_id"),
])
def test_trip_invalid_references(carriers, tractor_id, carrier_id, message):
    c, _, _, _ = carriers
    resp = _create_trip(c, tractor_id=tractor_id, carrier_id=carrier_id)
    assert resp.status_code == 400
    assert message in resp.get_json()["error"]


def test_removed_tractor_cannot_be_assigned_but_may_stay(carriers):
    c, _, alfa, _ = carriers
    tractor = _tractor(c, alfa, "REM-001")
    trip_id = _create_trip(c, carrier_id=alfa, tractor_id=tractor["id"]).get_json()["id"]
    c.put(f"/api/tractors/{tractor['id']}", json={"status": "poistettu"})
    # Jo valittu poistettu vetäjä saa jäädä keikalle muokkauksessa
    resp = c.put(f"/api/trips/{trip_id}", json=_trip_payload(carrier_id=alfa, tractor_id=tractor["id"]))
    assert resp.status_code == 200
    # Uudelle keikalle sitä ei voi valita
    resp = _create_trip(c, carrier_id=alfa, tractor_id=tractor["id"])
    assert resp.status_code == 400
    assert "poistettu" in resp.get_json()["error"]


def test_tractor_in_maintenance_can_be_planned(carriers):
    c, _, alfa, _ = carriers
    tractor = _tractor(c, alfa, "HUO-001", status="huollossa")
    assert _create_trip(c, carrier_id=alfa, tractor_id=tractor["id"]).status_code == 201


def test_locked_trip_cannot_change_tractor(carriers):
    c, db_path, alfa, _ = carriers
    tractor = _tractor(c, alfa, "LCK-001")
    trip_id = _create_trip(c, carrier_id=alfa).get_json()["id"]
    _set_trip_status(db_path, trip_id, "Laskutettu")
    resp = c.put(f"/api/trips/{trip_id}", json=_trip_payload(carrier_id=alfa, tractor_id=tractor["id"]))
    assert resp.status_code == 403


# ── truck_plate: palvelimen täyttämä kopio ────────────────────────────

def test_truck_plate_is_server_snapshot(carriers):
    c, db_path, alfa, _ = carriers
    first = _tractor(c, alfa, "SNP-001")
    second = _tractor(c, alfa, "SNP-002")
    resp = _create_trip(c, carrier_id=alfa, tractor_id=first["id"], truck_plate="KÄSIN-1")
    trip_id = resp.get_json()["id"]
    assert _trip(c, trip_id)["truck_plate"] == "SNP-001"  # asiakkaan arvo ohitetaan

    # Saman vetäjän uudelleentallennus keikalle ei muuta kopiota
    c.put(f"/api/trips/{trip_id}", json=_trip_payload(carrier_id=alfa, tractor_id=first["id"]))
    assert _trip(c, trip_id)["truck_plate"] == "SNP-001"

    # Vetäjän vaihto päivittää kopion, vetäjän poisto tyhjentää sen
    c.put(f"/api/trips/{trip_id}", json=_trip_payload(carrier_id=alfa, tractor_id=second["id"]))
    assert _trip(c, trip_id)["truck_plate"] == "SNP-002"
    c.put(f"/api/trips/{trip_id}", json=_trip_payload(carrier_id=alfa, tractor_id=None))
    assert _trip(c, trip_id)["truck_plate"] is None


def test_registration_change_updates_open_trips(carriers):
    """Rekisterin korjaus päivittää kopion kaikille laskuttamattomille keikoille."""
    c, db_path, alfa, _ = carriers
    tractor = _tractor(c, alfa, "FIX-001")
    trip_ids = [_create_trip(c, carrier_id=alfa, tractor_id=tractor["id"]).get_json()["id"]
                for _ in range(3)]
    for trip_id, status in zip(trip_ids, ["Suunniteltu", "Vahvistettu", "Toimitettu"]):
        _set_trip_status(db_path, trip_id, status)
    other = _create_trip(c, carrier_id=alfa).get_json()["id"]  # ei vetäjää: ei muutu

    resp = c.put(f"/api/tractors/{tractor['id']}", json={"registration_number": "fix-001b"})
    assert resp.status_code == 200
    assert resp.get_json()["updated_trips"] == 3
    for trip_id in trip_ids:
        trip = _trip(c, trip_id)
        assert (trip["truck_plate"], trip["tractor_registration"]) == ("FIX-001B", "FIX-001B")
    assert _trip(c, other)["truck_plate"] is None

    # Muu muutos kuin rekisteri ei koske keikkoihin
    resp = c.put(f"/api/tractors/{tractor['id']}", json={"status": "huollossa"})
    assert resp.get_json()["updated_trips"] == 0


def test_registration_change_keeps_invoiced_trips_frozen(carriers):
    """Laskutetun keikan kopio on jäädytetty: dokumentit on annettu vanhalla rekisterillä."""
    c, db_path, alfa, _ = carriers
    tractor = _tractor(c, alfa, "FRZ-001")
    invoiced = _create_trip(c, carrier_id=alfa, tractor_id=tractor["id"]).get_json()["id"]
    open_trip = _create_trip(c, carrier_id=alfa, tractor_id=tractor["id"]).get_json()["id"]
    _set_trip_status(db_path, invoiced, "Laskutettu")

    resp = c.put(f"/api/tractors/{tractor['id']}", json={"registration_number": "FRZ-002"})
    assert resp.get_json()["updated_trips"] == 1
    frozen = _trip(c, invoiced)
    assert frozen["truck_plate"] == "FRZ-001"
    assert frozen["tractor_registration"] == "FRZ-002"
    assert _trip(c, open_trip)["truck_plate"] == "FRZ-002"


def test_put_without_tractor_key_keeps_tractor(carriers):
    """Vanha TripForm ei lähetä tractor_id:tä: vetäjä ja kopio säilyvät,
    carrier-validointi koskee silti säilyvää vetäjää."""
    c, _, alfa, beta = carriers
    tractor = _tractor(c, alfa, "KEEP-01")
    trip_id = _create_trip(c, carrier_id=alfa, tractor_id=tractor["id"]).get_json()["id"]
    resp = c.put(f"/api/trips/{trip_id}", json=_trip_payload(carrier_id=alfa, notes="muokattu"))
    assert resp.status_code == 200
    trip = _trip(c, trip_id)
    assert (trip["tractor_id"], trip["truck_plate"], trip["notes"]) == (
        tractor["id"], "KEEP-01", "muokattu")
    resp = c.put(f"/api/trips/{trip_id}", json=_trip_payload(carrier_id=beta))
    assert resp.status_code == 400
    assert _trip(c, trip_id)["carrier_id"] == alfa


def test_legacy_truck_plate_kept_without_tractor(carriers):
    """Vanha keikka, jota migraatio ei linkittänyt: teksti säilyy muokkauksessa."""
    c, db_path, alfa, _ = carriers
    trip_id = _create_trip(c, carrier_id=alfa).get_json()["id"]
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE trips SET truck_plate = 'VANHA-1' WHERE id = ?", (trip_id,))
    conn.commit()
    conn.close()
    c.put(f"/api/trips/{trip_id}", json=_trip_payload(carrier_id=alfa, notes="muokattu"))
    assert _trip(c, trip_id)["truck_plate"] == "VANHA-1"


# ── Vetäjän carrierin vaihto ja kuljetusyhtiön poisto ─────────────────

def test_tractor_carrier_change_blocked_by_open_trip(carriers):
    c, db_path, alfa, beta = carriers
    tractor = _tractor(c, alfa, "MOV-001")
    trip_id = _create_trip(c, carrier_id=alfa, tractor_id=tractor["id"]).get_json()["id"]
    resp = c.put(f"/api/tractors/{tractor['id']}", json={"carrier_id": beta})
    assert resp.status_code == 409
    assert resp.get_json()["trip_count"] == 1
    # Laskutettu keikka ei estä (lukittu historia, truck_plate-kopio säilyy)
    _set_trip_status(db_path, trip_id, "Laskutettu")
    resp = c.put(f"/api/tractors/{tractor['id']}", json={"carrier_id": beta})
    assert resp.status_code == 200
    assert resp.get_json()["tractor"]["carrier_name"] == "Demo Beta Oy"


def test_carrier_delete_conflicts_when_it_has_tractors(carriers):
    c, _, alfa, beta = carriers
    tractor = _tractor(c, alfa, "CAR-001", status="poistettu")
    resp = c.delete(f"/api/carriers/{alfa}")
    assert resp.status_code == 409
    assert resp.get_json()["tractor_count"] == 1
    assert c.get(f"/api/tractors/{tractor['id']}").status_code == 200  # ei ketjupoistoa
    # Ilman vetäjiä poisto onnistuu
    assert c.delete(f"/api/carriers/{beta}").status_code == 200
    c.delete(f"/api/tractors/{tractor['id']}")
    assert c.delete(f"/api/carriers/{alfa}").status_code == 200


def test_trucks_api_removed(client):
    c, _ = client
    assert c.get("/api/trucks").status_code == 404


# ── Pikaluonti → valinta keikalle ─────────────────────────────────────

def test_quick_created_tractor_is_assignable_immediately(carriers):
    c, _, alfa, _ = carriers
    trip_id = _create_trip(c).get_json()["id"]  # keikalla ei vielä carrieria
    tractor = _tractor(c, alfa, "QCK-001")       # pikalomake: rekisteri, carrier, tyyppi
    resp = c.put(f"/api/trips/{trip_id}", json=_trip_payload(tractor_id=tractor["id"]))
    assert resp.status_code == 200
    trip = _trip(c, trip_id)
    assert (trip["tractor_id"], trip["carrier_id"], trip["truck_plate"]) == (
        tractor["id"], alfa, "QCK-001")
    # Uusi vetäjä näkyy carrierin suodatetussa listassa
    listed = c.get(f"/api/tractors?carrier_id={alfa}").get_json()
    assert [t["id"] for t in listed] == [tractor["id"]]


def test_quick_create_existing_registration_offers_existing(carriers):
    c, _, alfa, _ = carriers
    existing = _tractor(c, alfa, "QCK-002")
    resp = _create_tractor(c, alfa, "qck-002")
    assert resp.status_code == 409
    chosen = resp.get_json()["existing"]
    assert chosen["id"] == existing["id"]
    trip = _create_trip(c, tractor_id=chosen["id"])
    assert trip.status_code == 201


# ── Trailerit: yhteiset ominaisuudet ja pikaluonti ────────────────────

def test_trailer_quick_create(client):
    c, _ = client
    resp = c.post("/api/trailers", json={"plate_number": " QTR-001 ", "trailer_type": "Umpikaappi"})
    assert resp.status_code == 201
    body = resp.get_json()
    trailer = body["trailer"]
    assert body["id"] == trailer["id"]
    assert trailer["plate_number"] == "QTR-001"
    assert trailer["identifier"] == "QTR-001"  # oletuksena rekisterinumero
    assert trailer["features"] == FEATURES_OFF | {"temperature_controlled": True}
    assert "carrier_id" not in trailer

    resp = c.post("/api/trailers", json={"plate_number": "QTR-002", "trailer_type": "Megatrailer"})
    assert resp.get_json()["trailer"]["features"] == FEATURES_OFF

    # Valitaan heti keikalle (traileri on valinnainen, ei carrier-sidosta)
    trip = _create_trip(c, trailer_id=trailer["id"], trailer_type="Umpikaappi")
    assert trip.status_code == 201
    assert _trip(c, trip.get_json()["id"])["trailer_id"] == trailer["id"]


def test_trailer_quick_create_requires_plate_and_type(client):
    c, _ = client
    assert c.post("/api/trailers", json={"plate_number": "  ", "trailer_type": "Umpikaappi"}).status_code == 400
    assert c.post("/api/trailers", json={"plate_number": "QTR-003"}).status_code == 400


def test_trailer_and_tractor_share_feature_structure(carriers):
    c, _, alfa, _ = carriers
    tractor = _tractor(c, alfa, "FEA-001", features={"adr": True})
    resp = c.post("/api/trailers", json={"plate_number": "FEA-T01", "trailer_type": "Pressutrailer",
                                         "identifier": "FT-1", "features": {"adr": True}})
    trailer = resp.get_json()["trailer"]
    assert trailer["identifier"] == "FT-1"
    assert set(trailer["features"]) == set(tractor["features"]) == set(equipment.FEATURE_KEYS)
    assert trailer["features"] == tractor["features"]
    listed = next(t for t in c.get("/api/trailers").get_json() if t["id"] == trailer["id"])
    assert listed["features"] == trailer["features"]
    assert not set(equipment.FEATURE_KEYS) & set(listed)


def test_trailer_put_features(client):
    c, _ = client
    trailer = c.post("/api/trailers", json={"plate_number": "FEA-T02", "trailer_type": "Umpikaappi",
                                            "features": {"tail_lift": True}}).get_json()["trailer"]
    base = {"plate_number": "FEA-T02", "identifier": "FEA-T02", "trailer_type": "Umpikaappi"}
    # Vanha lomake ei lähetä featuresia → ominaisuudet säilyvät
    assert c.put(f"/api/trailers/{trailer['id']}", json=base).status_code == 200
    current = next(t for t in c.get("/api/trailers").get_json() if t["id"] == trailer["id"])
    assert current["features"] == trailer["features"]
    resp = c.put(f"/api/trailers/{trailer['id']}", json=base | {"features": {"tail_lift": False,
                                                                              "crane": True}})
    assert resp.status_code == 200
    current = next(t for t in c.get("/api/trailers").get_json() if t["id"] == trailer["id"])
    assert current["features"] == FEATURES_OFF | {"temperature_controlled": True, "crane": True}
    resp = c.put(f"/api/trailers/{trailer['id']}", json=base | {"features": {"nosturi": True}})
    assert resp.status_code == 400


# ── Demodata ──────────────────────────────────────────────────────────

def test_demo_tractors(demo_client):
    c, _ = demo_client
    tractors = c.get("/api/tractors?include_removed=1").get_json()
    assert len(tractors) == 14
    assert all("Demo" in t["carrier_name"] and "Demo" in t["make_model"] for t in tractors)
    trucks = [t for t in tractors if t["vehicle_type"] == "kuorma-auto"]
    assert trucks and all(t["max_weight"] and t["max_ldm"] and t["max_volume"] for t in trucks)
    assert all(t["max_weight"] is None for t in tractors if t["vehicle_type"] == "vetoauto")
    assert any(t["status"] == "huollossa" for t in tractors)


def test_demo_trips_tractor_carrier_matches(demo_client):
    c, _ = demo_client
    tractors = {t["id"]: t for t in c.get("/api/tractors?include_removed=1").get_json()}
    trips = c.get("/api/trips").get_json()
    assert len(trips) == 7
    for trip in trips:
        tractor = tractors[trip["tractor_id"]]
        assert tractor["carrier_id"] == trip["carrier_id"], trip["trip_id"]
        assert trip["truck_plate"] == tractor["registration_number"]


def test_demo_thermo_trailers_have_temperature_control(demo_client):
    c, _ = demo_client
    for trailer in c.get("/api/trailers").get_json():
        expected = trailer["trailer_type"] in equipment.TEMPERATURE_CONTROLLED_TRAILER_TYPES
        assert trailer["features"]["temperature_controlled"] is expected


# ── PUT: puuttuva kenttä säilyy, null tyhjentää ───────────────────────

def test_put_null_clears_optional_fields(carriers):
    c, _, alfa, _ = carriers
    truck = _tractor(c, alfa, "NUL-001", "kuorma-auto", make_model="Demo City 260",
                     emission_class="EURO VI", max_weight=8000, max_ldm=7, max_volume=40,
                     notes="Demo", status="huollossa",
                     features={"adr": True, "crane": True, "tail_lift": True})
    resp = c.put(f"/api/tractors/{truck['id']}", json={
        "make_model": None, "emission_class": None, "max_weight": None, "notes": None,
        "features": {"adr": None}})
    assert resp.status_code == 200
    updated = resp.get_json()["tractor"]
    assert updated == truck | {"make_model": None, "emission_class": None, "max_weight": None,
                               "notes": None, "features": truck["features"] | {"adr": False}}
    # features: null tyhjentää kaikki, status: null → oletus aktiivinen
    resp = c.put(f"/api/tractors/{truck['id']}", json={"features": None, "status": None})
    tractor = resp.get_json()["tractor"]
    assert tractor["features"] == FEATURES_OFF
    assert tractor["status"] == "aktiivinen"
    assert tractor["max_ldm"] == 7  # puuttuva kenttä säilyi


@pytest.mark.parametrize("field", ["registration_number", "carrier_id", "vehicle_type"])
def test_put_null_on_required_field_is_rejected(carriers, field):
    c, _, alfa, _ = carriers
    tractor = _tractor(c, alfa, "NUL-002")
    resp = c.put(f"/api/tractors/{tractor['id']}", json={field: None})
    assert resp.status_code == 400
    assert c.get(f"/api/tractors/{tractor['id']}").get_json() == tractor

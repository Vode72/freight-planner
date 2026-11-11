"""Trailerit (Alembic 0005): rekisterin ja tunnisteen yksikäsitteisyys, pikaluonti
409 + existing, Poistettu-status, poistosääntö ja id-pohjainen huoltohistoria."""
import sqlite3

import pytest


def _create(c, **data):
    return c.post("/api/trailers", json={"trailer_type": "Pressutrailer", **data})


def _trailer(c, **data):
    resp = _create(c, **data)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["trailer"]


def _listed(c, query=""):
    return {t["id"]: t for t in c.get(f"/api/trailers{query}").get_json()}


def _maintenance(c, trailer_id, mtype="OTHER"):
    resp = c.post(f"/api/trailers/{trailer_id}/maintenance", json={
        "maintenance_type": mtype, "date": "2026-11-01", "next_due": "2027-11-01", "notes": "Demo"})
    assert resp.status_code == 201
    return resp.get_json()


# ── Pikaluonti ja yksikäsitteisyys ────────────────────────────────────

def test_quick_create_normalizes_plate(client):
    c, _ = client
    trailer = _trailer(c, plate_number="  abc  123 ")
    assert trailer["plate_number"] == "ABC 123"
    assert trailer["identifier"] == "ABC 123"
    assert trailer["status"] == "Vapaa"


def test_swap_body_without_plate(client):
    c, _ = client
    trailer = _trailer(c, identifier=" VK-0001 ", plate_number="")
    assert trailer["plate_number"] is None
    assert trailer["identifier"] == "VK-0001"
    # Useampi rekisteritön sallittu (rekisteri uniikki vain kun annettu)
    assert _create(c, identifier="VK-0002").status_code == 201


def test_plate_or_identifier_required(client):
    c, _ = client
    resp = _create(c, plate_number=" ", identifier="")
    assert resp.status_code == 400
    assert "Rekisterinumero tai tunniste" in resp.get_json()["error"]
    assert c.post("/api/trailers", json={"plate_number": "NOTYPE-1"}).status_code == 400


@pytest.mark.parametrize("payload,field", [
    ({"plate_number": "dup-001", "identifier": "MUU-1"}, "plate_number"),
    ({"plate_number": " DUP-001 "}, "plate_number"),
    ({"plate_number": "UUSI-1", "identifier": "fx-1"}, "identifier"),
    ({"identifier": "Fx-1"}, "identifier"),
])
def test_create_conflict_returns_existing(client, payload, field):
    c, _ = client
    existing = _trailer(c, plate_number="DUP-001", identifier="FX-1")
    resp = _create(c, **payload)
    assert resp.status_code == 409
    body = resp.get_json()
    assert body["field"] == field
    assert body["existing"] == existing
    assert len(_listed(c)) == 1


def test_update_conflict_and_own_values(client):
    c, _ = client
    _trailer(c, plate_number="PUT-001", identifier="P-1")
    other = _trailer(c, plate_number="PUT-002", identifier="P-2")
    resp = c.put(f"/api/trailers/{other['id']}", json={"plate_number": "put-001"})
    assert resp.status_code == 409 and resp.get_json()["field"] == "plate_number"
    resp = c.put(f"/api/trailers/{other['id']}", json={"identifier": "p-1"})
    assert resp.status_code == 409 and resp.get_json()["field"] == "identifier"
    # Oma rekisteri/tunniste eri kirjainkoolla on sallittu
    resp = c.put(f"/api/trailers/{other['id']}", json={"plate_number": "put-002", "identifier": "p-2"})
    assert resp.status_code == 200
    assert resp.get_json()["trailer"]["identifier"] == "p-2"


def test_put_is_partial(client):
    c, _ = client
    trailer = _trailer(c, plate_number="PRT-001", identifier="PR-1", leasing_rate="42,50",
                       rental_rate=65, status="Käytössä", features={"adr": True})
    resp = c.put(f"/api/trailers/{trailer['id']}", json={"status": "Huollossa"})
    assert resp.status_code == 200
    assert resp.get_json()["trailer"] == trailer | {"status": "Huollossa"}


def test_put_without_identifier_uses_plate(client):
    """Vanha TrailerForm lähettää tyhjän tunnisteen: tunniste = rekisteri."""
    c, _ = client
    trailer = _trailer(c, plate_number="OLD-001", identifier="O-1")
    resp = c.put(f"/api/trailers/{trailer['id']}", json={
        "plate_number": "OLD-001", "identifier": "", "trailer_type": "Megatrailer"})
    assert resp.status_code == 200
    assert resp.get_json()["trailer"]["identifier"] == "OLD-001"


def test_put_404(client):
    c, _ = client
    assert c.put("/api/trailers/999", json={"status": "Vapaa"}).status_code == 404


# ── Poistettu-status ──────────────────────────────────────────────────

def test_invalid_status(client):
    c, _ = client
    assert _create(c, plate_number="ST-1", status="Romutettu").status_code == 400


def test_removed_trailers_hidden_by_default(client):
    c, _ = client
    active = _trailer(c, plate_number="ACT-001")
    removed = _trailer(c, plate_number="REM-001")
    assert c.put(f"/api/trailers/{removed['id']}", json={"status": "Poistettu"}).status_code == 200
    assert set(_listed(c)) == {active["id"]}
    assert set(_listed(c, "?include_removed=1")) == {active["id"], removed["id"]}
    meta = c.get("/api/equipment-meta").get_json()
    assert meta["trailer_statuses"] == ["Vapaa", "Käytössä", "Huollossa", "Poistettu"]


def test_removed_trailer_cannot_be_assigned_but_may_stay(client):
    c, _ = client
    trailer = _trailer(c, plate_number="RTR-001")
    trip_id = c.post("/api/trips", json={"trailer_id": trailer["id"]}).get_json()["id"]
    c.put(f"/api/trailers/{trailer['id']}", json={"status": "Poistettu"})
    # Jo valittu saa jäädä keikalle
    assert c.put(f"/api/trips/{trip_id}", json={"trailer_id": trailer["id"]}).status_code == 200
    resp = c.post("/api/trips", json={"trailer_id": trailer["id"]})
    assert resp.status_code == 400
    assert "poistettu käytöstä" in resp.get_json()["error"]
    assert c.post("/api/trips", json={"trailer_id": 999}).status_code == 400


# ── Poisto: 409 historian tai keikkojen kanssa ────────────────────────

def test_delete_unused_trailer(client):
    c, _ = client
    trailer = _trailer(c, plate_number="DEL-001")
    assert c.delete(f"/api/trailers/{trailer['id']}").status_code == 200
    assert c.delete(f"/api/trailers/{trailer['id']}").status_code == 404


def test_delete_with_maintenance_history_conflicts(client):
    c, _ = client
    trailer = _trailer(c, plate_number="DEL-002")
    _maintenance(c, trailer["id"], "INSPECTION")
    resp = c.delete(f"/api/trailers/{trailer['id']}")
    assert resp.status_code == 409
    body = resp.get_json()
    assert (body["maintenance_count"], body["trip_count"]) == (1, 0)
    assert "Poistettu" in body["error"]
    assert trailer["id"] in _listed(c)


def test_delete_with_invoiced_trip_conflicts(client):
    c, db_path = client
    trailer = _trailer(c, plate_number="DEL-003")
    trip_id = c.post("/api/trips", json={"trailer_id": trailer["id"]}).get_json()["id"]
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE trips SET status = 'Laskutettu' WHERE id = ?", (trip_id,))
    conn.commit()
    conn.close()
    resp = c.delete(f"/api/trailers/{trailer['id']}")
    assert resp.status_code == 409
    assert resp.get_json()["trip_count"] == 1
    # Ohjattu tie: status Poistettu
    resp = c.put(f"/api/trailers/{trailer['id']}", json={"status": "Poistettu"})
    assert resp.status_code == 200
    assert trailer["id"] not in _listed(c)


# ── Huoltohistoria trailerin id:llä ───────────────────────────────────

def test_plate_change_keeps_maintenance_history(client):
    c, db_path = client
    trailer = _trailer(c, plate_number="HIS-001")
    first = _maintenance(c, trailer["id"], "INSPECTION")
    assert first["trailer_id"] == trailer["id"]
    resp = c.put(f"/api/trailers/{trailer['id']}", json={"plate_number": "HIS-999"})
    assert resp.status_code == 200
    _maintenance(c, trailer["id"], "OTHER")
    history = c.get(f"/api/trailers/{trailer['id']}/maintenance").get_json()
    assert len(history) == 2 and {h["trailer_id"] for h in history} == {trailer["id"]}
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT DISTINCT typeof(trailer_id) FROM trailer_maintenance").fetchall() == [
        ("integer",)]
    conn.close()


def test_new_trailer_with_old_plate_does_not_inherit_history(client):
    """Ennen 0005:ttä historia periytyi samalla rekisterillä luodulle uudelle trailerille."""
    c, _ = client
    old = _trailer(c, plate_number="INH-001", identifier="I-OLD")
    _maintenance(c, old["id"])
    c.put(f"/api/trailers/{old['id']}", json={"plate_number": "INH-OLD", "status": "Poistettu"})
    new = _trailer(c, plate_number="INH-001", identifier="I-NEW")
    assert c.get(f"/api/trailers/{new['id']}/maintenance").get_json() == []
    assert len(c.get(f"/api/trailers/{old['id']}/maintenance").get_json()) == 1


def test_maintenance_404(client):
    c, _ = client
    assert c.get("/api/trailers/999/maintenance").status_code == 404
    assert c.post("/api/trailers/999/maintenance", json={"date": "2026-01-01"}).status_code == 404


def test_demo_maintenance_linked_by_id(demo_client):
    c, db_path = demo_client
    conn = sqlite3.connect(db_path)
    rows = conn.execute("""
        SELECT m.trailer_id, typeof(m.trailer_id), t.id FROM trailer_maintenance m
        LEFT JOIN trailers t ON t.id = m.trailer_id""").fetchall()
    conn.close()
    assert rows and all(r[1] == "integer" and r[0] == r[2] for r in rows)
    urv = next(t for t in _listed(c).values() if t["plate_number"] == "URV-001")
    assert len(c.get(f"/api/trailers/{urv['id']}/maintenance").get_json()) == 2

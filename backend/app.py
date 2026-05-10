import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_NAME = "freight.db"

TRAILER_SPECS = {
    "Umpikaappi": {
        "side_loading": False,
        "temperature_controlled": True,
        "dual_zone": False,
        "max_weight": 23500,
        "max_loading_meters": 13.6,
        "max_volume": 90
    },
    "Sivuaukeava": {
        "side_loading": True,
        "temperature_controlled": True,
        "dual_zone": False,
        "max_weight": 23500,
        "max_loading_meters": 13.6,
        "max_volume": 90
    },
    "Umpikaappi 2-koneinen": {
        "side_loading": False,
        "temperature_controlled": True,
        "dual_zone": True,
        "max_weight": 23500,
        "max_loading_meters": 13.6,
        "max_volume": 90
    },
    "Pressutrailer": {
        "side_loading": True,
        "temperature_controlled": False,
        "dual_zone": False,
        "max_weight": 24000,
        "max_loading_meters": 13.6,
        "max_volume": 90
    },
    "Megatrailer": {
        "side_loading": True,
        "temperature_controlled": False,
        "dual_zone": False,
        "max_weight": 24000,
        "max_loading_meters": 13.6,
        "max_volume": 100
    }
}

INCOTERMS = ["EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP"]
TRANSPORT_TYPES = ["Suora", "Terminaalin kautta", "Groupage"]
STATUSES = ["Suunniteltu", "Vahvistettu", "Käynnissä", "Toimitettu", "Laskutettu"]

FERRY_ROUTES = [
    {"route": "Helsinki - Travemünde", "carrier": "Finnlines", "price": 1050},
    {"route": "Hanko - Lübeck", "carrier": "Transfennica", "price": 1010},
    {"route": "Hanko - Rostock", "carrier": "Finnlines", "price": 750},
    {"route": "Kotka - Antwerpen", "carrier": "Transfennica", "price": 1800},
]

COST_CODES = [
    {"code": "100", "description": "SPOT PRICE", "type": "revenue"},
    {"code": "120", "description": "FREIGHT", "type": "revenue"},
    {"code": "200", "description": "POLTTOAINELISÄ", "type": "cost"},
    {"code": "210", "description": "KOTIMAAN AJO", "type": "cost"},
    {"code": "220", "description": "MANTEREEN AJO", "type": "cost"},
    {"code": "300", "description": "SAKSAN TIEMAKSU", "type": "cost"},
    {"code": "310", "description": "HOLLANTI + SAKSA TIEMAKSU", "type": "cost"},
    {"code": "400", "description": "TRAILERVUOKRA (osto)", "type": "cost"},
    {"code": "401", "description": "TRAILERVUOKRA (myynti)", "type": "revenue"},    
    {"code": "410", "description": "TRAILERIN TANKKAUS", "type": "cost"},
    {"code": "500", "description": "LAUTTAKUSTANNUS", "type": "cost"},
    {"code": "510", "description": "SATAMAMAKSU", "type": "cost"},
    {"code": "600", "description": "ADR-LISÄ", "type": "cost"},
    {"code": "610", "description": "LÄMPÖTILALISÄ", "type": "cost"},
    {"code": "700", "description": "KÄSITTELYMAKSU", "type": "cost"},
    {"code": "799", "description": "MUUT KULUT", "type": "cost"},
    {"code": "800", "description": "ODOTUSAIKA", "type": "cost"},
    {"code": "810", "description": "LISÄKÄSITTELY", "type": "cost"},
    {"code": "820", "description": "MUU KULU", "type": "cost"},
    {"code": "830", "description": "TRAILERIN YLIKÄYTTÖ (osto)", "type": "cost"},
    {"code": "831", "description": "TRAILERIN YLIKÄYTTÖ (myynti)", "type": "revenue"},
]

PALLET_TYPES = [
    {"type": "FIN-lava", "width": 1.0, "length": 1.2, "height": None},
    {"type": "EUR-lava", "width": 0.8, "length": 1.2, "height": None},
    {"type": "Teholava", "width": None, "length": None, "height": None},
    {"type": "IBC-kontti", "width": 1.0, "length": 1.2, "height": 1.15},
    {"type": "Muu", "width": None, "length": None, "height": None},
]

STATUS_FLOW = {
    "Suunniteltu": {"next": "Vahvistettu", "prev": None},
    "Vahvistettu": {"next": "Käynnissä", "prev": "Suunniteltu"},
    "Käynnissä": {"next": "Toimitettu", "prev": "Vahvistettu"},
    "Toimitettu": {"next": "Laskutettu", "prev": "Käynnissä"},
    "Laskutettu": {"next": None, "prev": None}
}


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def calculate_loading_meters(width, length, quantity):
    if not width or not length:
        return 0
    return round((width * length / 2.4) * quantity, 2)


def calculate_volume(width, length, height, quantity):
    if not width or not length or not height:
        return 0
    return round(width * length * height * quantity, 2)


def generate_trip_id():
    year = datetime.now().year
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) as c FROM trips").fetchone()["c"]
    conn.close()
    return f"TRP-{year}-{str(count + 1).zfill(3)}"


def generate_order_id():
    year = datetime.now().year
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) as c FROM orders").fetchone()["c"]
    conn.close()
    return f"ORD-{year}-{str(count + 1).zfill(3)}"


def generate_order_reference():
    year = datetime.now().year
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) as c FROM orders").fetchone()["c"]
    conn.close()
    return f"HEL-{year}-{str(count + 1).zfill(3)}"


def is_locked(status):
    return status == "Laskutettu"


def get_trip_capacity(trip_id, conn):
    orders = conn.execute(
        "SELECT weight, loading_meters, volume FROM orders WHERE trip_id = ?",
        (trip_id,)
    ).fetchall()
    return {
        "total_weight": round(sum(o["weight"] for o in orders), 2),
        "total_loading_meters": round(sum(o["loading_meters"] for o in orders), 2),
        "total_volume": round(sum(o["volume"] for o in orders), 2)
    }


# ===== AUTH =====

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    if username == "demo" and password == "freight2024":
        return jsonify({"success": True, "message": "Kirjautuminen onnistui"})
    return jsonify({"success": False, "message": "Väärä käyttäjätunnus tai salasana"}), 401


# ===== REFERENCE DATA =====

@app.route("/api/trailer-types", methods=["GET"])
def get_trailer_types():
    return jsonify(list(TRAILER_SPECS.keys()))


@app.route("/api/trailer-specs", methods=["GET"])
def get_trailer_specs():
    return jsonify(TRAILER_SPECS)


@app.route("/api/incoterms", methods=["GET"])
def get_incoterms():
    return jsonify(INCOTERMS)


@app.route("/api/transport-types", methods=["GET"])
def get_transport_types():
    return jsonify(TRANSPORT_TYPES)


@app.route("/api/statuses", methods=["GET"])
def get_statuses():
    return jsonify(STATUSES)


@app.route("/api/ferry-routes", methods=["GET"])
def get_ferry_routes():
    return jsonify(FERRY_ROUTES)


@app.route("/api/cost-codes", methods=["GET"])
def get_cost_codes():
    return jsonify(COST_CODES)


@app.route("/api/pallet-types", methods=["GET"])
def get_pallet_types():
    return jsonify(PALLET_TYPES)


@app.route("/api/next-order-reference", methods=["GET"])
def get_next_order_reference():
    return jsonify({"reference": generate_order_reference()})


# ===== TRAILERS =====

@app.route("/api/trailers", methods=["GET"])
def get_trailers():
    conn = get_db_connection()
    trailers = conn.execute(
        "SELECT * FROM trailers ORDER BY trailer_type, plate_number"
    ).fetchall()
    conn.close()
    return jsonify([dict(t) for t in trailers])


@app.route("/api/trailers", methods=["POST"])
def create_trailer():
    data = request.get_json()
    if not data or not data.get("plate_number") or not data.get("trailer_type"):
        return jsonify({"error": "Rekisterinumero ja tyyppi ovat pakollisia"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trailers (plate_number, identifier, trailer_type, leasing_company, leasing_rate, rental_rate, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("plate_number"),
        data.get("identifier", ""),
        data.get("trailer_type"),
        data.get("leasing_company", "TIP Trailer Services"),
        float(data.get("leasing_rate", 0)),
        float(data.get("rental_rate", 0)),
        data.get("status", "Vapaa")
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"message": "Traileri luotu", "id": new_id}), 201


@app.route("/api/trailers/<int:trailer_id>", methods=["PUT"])
def update_trailer(trailer_id):
    conn = get_db_connection()
    if not conn.execute("SELECT id FROM trailers WHERE id=?", (trailer_id,)).fetchone():
        conn.close()
        return jsonify({"error": "Traileria ei löydy"}), 404
    data = request.get_json()
    conn.execute("""
        UPDATE trailers SET plate_number=?, identifier=?, trailer_type=?,
            leasing_company=?, leasing_rate=?, rental_rate=?, status=?
        WHERE id=?
    """, (
        data.get("plate_number"),
        data.get("identifier", ""),
        data.get("trailer_type"),
        data.get("leasing_company", "TIP Trailer Services"),
        float(data.get("leasing_rate", 0)),
        float(data.get("rental_rate", 0)),
        data.get("status", "Vapaa"),
        trailer_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"message": "Traileri päivitetty"})


@app.route("/api/trailers/<int:trailer_id>", methods=["DELETE"])
def delete_trailer(trailer_id):
    conn = get_db_connection()
    if not conn.execute("SELECT id FROM trailers WHERE id=?", (trailer_id,)).fetchone():
        conn.close()
        return jsonify({"error": "Traileria ei löydy"}), 404
    active = conn.execute("""
        SELECT COUNT(*) as c FROM trips
        WHERE trailer_id=? AND status NOT IN ('Laskutettu')
    """, (trailer_id,)).fetchone()["c"]
    if active > 0:
        conn.close()
        return jsonify({"error": f"Trailerilla on {active} aktiivista keikkaa — poista ensin keikkalinkitykset"}), 400
    conn.execute("DELETE FROM trailers WHERE id=?", (trailer_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Traileri poistettu"})


# ===== CARRIERS =====

@app.route("/api/carriers", methods=["GET"])
def get_carriers():
    conn = get_db_connection()
    carriers = conn.execute("SELECT * FROM carriers ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(c) for c in carriers])


@app.route("/api/carriers", methods=["POST"])
def create_carrier():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Nimi on pakollinen"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO carriers (name, country, city, business_id, contact_person, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get("name"),
        data.get("country", "FI"),
        data.get("city", ""),
        data.get("business_id"),
        data.get("contact_person"),
        data.get("phone")
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"message": "Kuljetusyhtiö luotu", "id": new_id}), 201


@app.route("/api/carriers/<int:carrier_id>", methods=["PUT"])
def update_carrier(carrier_id):
    conn = get_db_connection()
    if not conn.execute("SELECT id FROM carriers WHERE id=?", (carrier_id,)).fetchone():
        conn.close()
        return jsonify({"error": "Kuljetusyhtiötä ei löydy"}), 404
    data = request.get_json()
    conn.execute("""
        UPDATE carriers SET name=?, country=?, city=?, business_id=?, contact_person=?, phone=?
        WHERE id=?
    """, (
        data.get("name"),
        data.get("country", "FI"),
        data.get("city", ""),
        data.get("business_id"),
        data.get("contact_person"),
        data.get("phone"),
        carrier_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"message": "Kuljetusyhtiö päivitetty"})


@app.route("/api/carriers/<int:carrier_id>", methods=["DELETE"])
def delete_carrier(carrier_id):
    conn = get_db_connection()
    if not conn.execute("SELECT id FROM carriers WHERE id=?", (carrier_id,)).fetchone():
        conn.close()
        return jsonify({"error": "Kuljetusyhtiötä ei löydy"}), 404
    active = conn.execute("""
        SELECT COUNT(*) as c FROM trips
        WHERE carrier_id=? AND status NOT IN ('Laskutettu')
    """, (carrier_id,)).fetchone()["c"]
    if active > 0:
        conn.close()
        return jsonify({"error": f"Kuljetusyhtiöllä on {active} aktiivista keikkaa — poista ensin keikkalinkitykset"}), 400
    conn.execute("DELETE FROM trucks WHERE carrier_id=?", (carrier_id,))
    conn.execute("DELETE FROM carriers WHERE id=?", (carrier_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Kuljetusyhtiö poistettu"})


# ===== TRUCKS =====

@app.route("/api/trucks", methods=["GET"])
def get_trucks():
    carrier_id = request.args.get("carrier_id")
    conn = get_db_connection()
    if carrier_id:
        trucks = conn.execute("""
            SELECT t.*, c.name as carrier_name
            FROM trucks t
            JOIN carriers c ON t.carrier_id = c.id
            WHERE t.carrier_id = ?
            ORDER BY t.plate_number
        """, (carrier_id,)).fetchall()
    else:
        trucks = conn.execute("""
            SELECT t.*, c.name as carrier_name
            FROM trucks t
            JOIN carriers c ON t.carrier_id = c.id
            ORDER BY c.name, t.plate_number
        """).fetchall()
    conn.close()
    return jsonify([dict(t) for t in trucks])


@app.route("/api/trucks", methods=["POST"])
def create_truck():
    data = request.get_json()
    if not data or not data.get("plate_number") or not data.get("carrier_id"):
        return jsonify({"error": "Rekisterinumero ja kuljetusyhtiö ovat pakollisia"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO trucks (plate_number, carrier_id, status) VALUES (?, ?, ?)",
        (data.get("plate_number"), data.get("carrier_id"), data.get("status", "Vapaa"))
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"message": "Vetäjä luotu", "id": new_id}), 201


@app.route("/api/trucks/<int:truck_id>", methods=["PUT"])
def update_truck(truck_id):
    conn = get_db_connection()
    if not conn.execute("SELECT id FROM trucks WHERE id=?", (truck_id,)).fetchone():
        conn.close()
        return jsonify({"error": "Vetäjää ei löydy"}), 404
    data = request.get_json()
    conn.execute(
        "UPDATE trucks SET plate_number=?, carrier_id=?, status=? WHERE id=?",
        (data.get("plate_number"), data.get("carrier_id"), data.get("status", "Vapaa"), truck_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Vetäjä päivitetty"})


@app.route("/api/trucks/<int:truck_id>", methods=["DELETE"])
def delete_truck(truck_id):
    conn = get_db_connection()
    if not conn.execute("SELECT id FROM trucks WHERE id=?", (truck_id,)).fetchone():
        conn.close()
        return jsonify({"error": "Vetäjää ei löydy"}), 404
    conn.execute("DELETE FROM trucks WHERE id=?", (truck_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Vetäjä poistettu"})

@app.route("/api/route-match", methods=["GET"])
def route_match():
    order_country = request.args.get("order_country", "")
    order_zip = request.args.get("order_zip", "")
    trip_country = request.args.get("trip_country", "")
    trip_zip = request.args.get("trip_zip", "")
    match = get_route_match(order_country, order_zip, trip_country, trip_zip)
    return jsonify({"match": match})


# ===== TRIPS =====

@app.route("/api/trips", methods=["GET"])
def get_trips():
    conn = get_db_connection()
    trips = conn.execute("""
        SELECT t.*,
               tr.plate_number, tr.identifier, tr.trailer_type as trailer_type_name,
               c.name as carrier_name, c.country as carrier_country,
               COUNT(o.id) as order_count,
               COALESCE(SUM(o.weight), 0) as total_weight,
               COALESCE(SUM(o.loading_meters), 0) as total_loading_meters,
               COALESCE(SUM(o.volume), 0) as total_volume
        FROM trips t
        LEFT JOIN trailers tr ON t.trailer_id = tr.id
        LEFT JOIN carriers c ON t.carrier_id = c.id
        LEFT JOIN orders o ON t.id = o.trip_id
        GROUP BY t.id
        ORDER BY t.created_at DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(t) for t in trips])


@app.route("/api/trips/<int:trip_id>", methods=["GET"])
def get_trip(trip_id):
    conn = get_db_connection()
    trip = conn.execute("""
        SELECT t.*,
               tr.plate_number, tr.identifier, tr.trailer_type as trailer_type_name,
               c.name as carrier_name, c.country as carrier_country
        FROM trips t
        LEFT JOIN trailers tr ON t.trailer_id = tr.id
        LEFT JOIN carriers c ON t.carrier_id = c.id
        WHERE t.id = ?
    """, (trip_id,)).fetchone()

    if not trip:
        conn.close()
        return jsonify({"error": "Keikkaa ei löytynyt"}), 404

    orders = conn.execute(
        "SELECT * FROM orders WHERE trip_id = ? ORDER BY id",
        (trip_id,)
    ).fetchall()

    costs = conn.execute(
        "SELECT * FROM costs WHERE trip_id = ? ORDER BY cost_code",
        (trip_id,)
    ).fetchall()

    capacity = get_trip_capacity(trip_id, conn)
    conn.close()

    trailer_type = trip["trailer_type"]
    specs = TRAILER_SPECS.get(trailer_type, {})

    result = dict(trip)
    result["orders"] = [dict(o) for o in orders]
    result["costs"] = [dict(c) for c in costs]
    result["capacity"] = capacity
    result["max_weight"] = specs.get("max_weight", 24000)
    result["max_loading_meters"] = specs.get("max_loading_meters", 13.6)
    result["max_volume"] = specs.get("max_volume", 90)

    total_costs = sum(c["amount"] for c in costs if c["cost_type"] == "cost")
    total_revenue = sum(c["amount"] for c in costs if c["cost_type"] == "revenue")
    result["total_costs"] = round(total_costs, 2)
    result["total_revenue"] = round(total_revenue, 2)
    result["margin"] = round(total_revenue - total_costs, 2)
    result["margin_percent"] = round(
        (result["margin"] / total_revenue * 100), 2
    ) if total_revenue > 0 else 0

    return jsonify(result)


@app.route("/api/trips", methods=["POST"])
def create_trip():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Puuttuva data"}), 400

    trip_id = generate_trip_id()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trips (
            trip_id, status,
            first_pickup_country, first_pickup_zip, first_pickup_city,
            trip_end_country, trip_end_zip, trip_end_city,
            transport_type, carrier_id, trailer_id, trailer_type, truck_plate,
            loading_date, loading_time_start, loading_time_end,
            delivery_date, delivery_time_start, delivery_time_end,
            fixed_delivery_date, ferry_route, ferry_departure, ferry_arrival,
            adr, tail_lift, temperature_controlled,
            loading_instructions, notes
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        trip_id,
        "Suunniteltu",
        data.get("first_pickup_country"),
        data.get("first_pickup_zip"),
        data.get("first_pickup_city"),
        data.get("trip_end_country"),
        data.get("trip_end_zip"),
        data.get("trip_end_city"),
        data.get("transport_type", "Suora"),
        data.get("carrier_id"),
        data.get("trailer_id"),
        data.get("trailer_type"),
        data.get("truck_plate"),
        data.get("loading_date"),
        data.get("loading_time_start"),
        data.get("loading_time_end"),
        data.get("delivery_date"),
        data.get("delivery_time_start"),
        data.get("delivery_time_end"),
        int(data.get("fixed_delivery_date", False)),
        data.get("ferry_route"),
        data.get("ferry_departure"),
        data.get("ferry_arrival"),
        int(data.get("adr", False)),
        int(data.get("tail_lift", False)),
        int(data.get("temperature_controlled", False)),
        data.get("loading_instructions"),
        data.get("notes")
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"message": "Keikka luotu", "id": new_id, "trip_id": trip_id}), 201


@app.route("/api/trips/<int:trip_id>", methods=["PUT"])
def update_trip(trip_id):
    conn = get_db_connection()
    trip = conn.execute("SELECT status FROM trips WHERE id = ?", (trip_id,)).fetchone()

    if not trip:
        conn.close()
        return jsonify({"error": "Keikkaa ei löytynyt"}), 404

    if is_locked(trip["status"]):
        conn.close()
        return jsonify({"error": "Laskutettu keikka on lukittu"}), 403

    data = request.get_json()
    conn.execute("""
        UPDATE trips SET
            first_pickup_country=?, first_pickup_zip=?, first_pickup_city=?,
            trip_end_country=?, trip_end_zip=?, trip_end_city=?,
            transport_type=?, carrier_id=?, trailer_id=?, trailer_type=?, truck_plate=?,
            loading_date=?, loading_time_start=?, loading_time_end=?,
            delivery_date=?, delivery_time_start=?, delivery_time_end=?,
            fixed_delivery_date=?, ferry_route=?, ferry_departure=?, ferry_arrival=?,
            adr=?, tail_lift=?, temperature_controlled=?,
            loading_instructions=?, notes=?
        WHERE id=?
    """, (
        data.get("first_pickup_country"),
        data.get("first_pickup_zip"),
        data.get("first_pickup_city"),
        data.get("trip_end_country"),
        data.get("trip_end_zip"),
        data.get("trip_end_city"),
        data.get("transport_type"),
        data.get("carrier_id"),
        data.get("trailer_id"),
        data.get("trailer_type"),
        data.get("truck_plate"),
        data.get("loading_date"),
        data.get("loading_time_start"),
        data.get("loading_time_end"),
        data.get("delivery_date"),
        data.get("delivery_time_start"),
        data.get("delivery_time_end"),
        int(data.get("fixed_delivery_date", False)),
        data.get("ferry_route"),
        data.get("ferry_departure"),
        data.get("ferry_arrival"),
        int(data.get("adr", False)),
        int(data.get("tail_lift", False)),
        int(data.get("temperature_controlled", False)),
        data.get("loading_instructions"),
        data.get("notes"),
        trip_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"message": "Keikka päivitetty"})

@app.route("/api/trips/<int:trip_id>/status", methods=["PUT"])
def update_trip_status(trip_id):
    conn = get_db_connection()
    trip = conn.execute("SELECT status FROM trips WHERE id = ?", (trip_id,)).fetchone()

    if not trip:
        conn.close()
        return jsonify({"error": "Keikkaa ei löytynyt"}), 404

    if is_locked(trip["status"]):
        conn.close()
        return jsonify({"error": "Laskutettu keikka on lukittu"}), 403

    data = request.get_json()
    new_status = data.get("status")

    if new_status not in STATUSES:
        conn.close()
        return jsonify({"error": "Virheellinen status"}), 400

    conn.execute("UPDATE trips SET status = ? WHERE id = ?", (new_status, trip_id))

    if new_status == "Vahvistettu":
        trip_data = conn.execute("""
            SELECT t.*, tr.leasing_rate, tr.rental_rate
            FROM trips t
            LEFT JOIN trailers tr ON t.trailer_id = tr.id
            WHERE t.id = ?
        """, (trip_id,)).fetchone()

        if trip_data and trip_data["loading_date"] and trip_data["delivery_date"] and trip_data["trailer_id"]:
            from datetime import date
            loading = date.fromisoformat(trip_data["loading_date"])
            delivery = date.fromisoformat(trip_data["delivery_date"])
            days = (delivery - loading).days + 1

            if days > 0 and trip_data["leasing_rate"] and trip_data["rental_rate"]:
                existing = conn.execute("""
                    SELECT id FROM costs
                    WHERE trip_id = ? AND cost_code IN ('400', '401')
                """, (trip_id,)).fetchone()

                if not existing:
                    osto = round(days * trip_data["leasing_rate"], 2)
                    myynti = round(days * trip_data["rental_rate"], 2)

                    conn.execute("""
                        INSERT INTO costs (trip_id, cost_code, description, amount, cost_type)
                        VALUES (?, '400', ?, ?, 'cost')
                    """, (trip_id, f"TRAILERVUOKRA (osto) {days} pv x {trip_data['leasing_rate']} €", osto))

                    conn.execute("""
                        INSERT INTO costs (trip_id, cost_code, description, amount, cost_type)
                        VALUES (?, '401', ?, ?, 'revenue')
                    """, (trip_id, f"TRAILERVUOKRA (myynti) {days} pv x {trip_data['rental_rate']} €", myynti))

    conn.commit()
    conn.close()
    return jsonify({"message": "Status päivitetty"})


@app.route("/api/trips/<int:trip_id>/confirm-invoice", methods=["POST"])
def confirm_invoice(trip_id):
    conn = get_db_connection()
    trip = conn.execute("SELECT status FROM trips WHERE id = ?", (trip_id,)).fetchone()

    if not trip:
        conn.close()
        return jsonify({"error": "Keikkaa ei löytynyt"}), 404

    if trip["status"] != "Toimitettu":
        conn.close()
        return jsonify({"error": "Keikan pitää olla Toimitettu-tilassa"}), 400

    conn.execute("UPDATE trips SET status = 'Laskutettu' WHERE id = ?", (trip_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Lasku vahvistettu"})


@app.route("/api/trips/<int:trip_id>", methods=["DELETE"])
def delete_trip(trip_id):
    conn = get_db_connection()
    trip = conn.execute("SELECT status FROM trips WHERE id = ?", (trip_id,)).fetchone()

    if not trip:
        conn.close()
        return jsonify({"error": "Keikkaa ei löytynyt"}), 404

    if is_locked(trip["status"]):
        conn.close()
        return jsonify({"error": "Laskutettu keikka on lukittu"}), 403

    conn.execute("UPDATE orders SET trip_id = NULL, status = 'Vapaa' WHERE trip_id = ?", (trip_id,))
    conn.execute("DELETE FROM costs WHERE trip_id = ?", (trip_id,))
    conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Keikka poistettu"})


def get_route_match(order_country, order_zip, trip_country, trip_zip):
    """
    Vertaa orderin purkupaikan ja tripin maaranpaan yhteensopivuutta.
    Palauttaa: 'good', 'warning', tai 'bad'
    """
    if not order_country or not trip_country:
        return "warning"
    ...

    # Sama maa
    if order_country == trip_country:
        if order_zip and trip_zip:
            # Sama postialue (1. numero sama)
            if order_zip[0] == trip_zip[0]:
                return "good"
            else:
                return "warning"
        return "good"

    # Naapurimaat
    NEIGHBORS = {
        "FI": ["EE", "SE", "NO"],
        "SE": ["NO", "DK", "FI"],
        "NO": ["SE", "FI"],
        "DK": ["SE", "DE"],
        "DE": ["NL", "BE", "LU", "FR", "CH", "AT", "PL", "CZ", "DK"],
        "NL": ["BE", "DE", "LU"],
        "BE": ["NL", "DE", "LU", "FR"],
        "LU": ["BE", "DE", "FR"],
        "FR": ["BE", "LU", "DE", "CH", "IT", "ES"],
        "PL": ["DE", "CZ", "SK", "UA", "BY", "LT"],
        "EE": ["FI", "LV"],
        "LV": ["EE", "LT"],
        "LT": ["LV", "PL", "BY"],
        "AT": ["DE", "CH", "IT", "SI", "SK", "HU", "CZ"],
        "CH": ["DE", "AT", "FR", "IT"],
        "IT": ["FR", "CH", "AT", "SI"],
        "ES": ["FR", "PT"],
    }

    if trip_country in NEIGHBORS.get(order_country, []):
        return "warning"

    return "bad"

    conn.execute("UPDATE orders SET trip_id = NULL, status = 'Vapaa' WHERE trip_id = ?", (trip_id,))
    conn.execute("DELETE FROM costs WHERE trip_id = ?", (trip_id,))
    conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Keikka poistettu"})


# ===== ORDERS =====

@app.route("/api/orders", methods=["GET"])
def get_orders():
    status_filter = request.args.get("status")
    conn = get_db_connection()
    if status_filter:
        orders = conn.execute(
            "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC",
            (status_filter,)
        ).fetchall()
    else:
        orders = conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return jsonify([dict(o) for o in orders])


@app.route("/api/orders/<int:order_id>", methods=["GET"])
def get_order(order_id):
    conn = get_db_connection()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    if not order:
        return jsonify({"error": "Orderia ei löytynyt"}), 404
    return jsonify(dict(order))


@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Puuttuva data"}), 400

    order_id = generate_order_id()

    width = float(data.get("pallet_width", 0) or 0)
    length = float(data.get("pallet_length", 0) or 0)
    height = float(data.get("pallet_height", 0) or 0)
    quantity = int(data.get("quantity", 1) or 1)

    loading_meters = calculate_loading_meters(width, length, quantity)
    volume = calculate_volume(width, length, height, quantity)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (
            order_id, status,
            order_reference, pickup_reference, goods_description, incoterms,
            consignor_name, consignor_address, consignor_country,
            consignee_name, consignee_address, consignee_country,
            loading_point_name, loading_point_country, loading_point_zip, loading_point_city,
            unloading_point_name, unloading_point_country, unloading_point_zip, unloading_point_city,
            pallet_type, quantity, pallet_width, pallet_length, pallet_height,
            loading_meters, volume, weight,
            stackable, adr, tail_lift, insured, high_value,
            pre_advise, time_slot_loading, time_slot_delivery,
            min_temperature, max_temperature, temperature_monitoring, required_compartment,
            loading_instructions,
            loading_date, loading_time_start, loading_time_end,
            delivery_date, delivery_time_start, delivery_time_end
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        order_id, "Vapaa",
        data.get("order_reference"),
        data.get("pickup_reference"),
        data.get("goods_description"),
        data.get("incoterms"),
        data.get("consignor_name"),
        data.get("consignor_address"),
        data.get("consignor_country"),
        data.get("consignee_name"),
        data.get("consignee_address"),
        data.get("consignee_country"),
        data.get("loading_point_name"),
        data.get("loading_point_country"),
        data.get("loading_point_zip"),
        data.get("loading_point_city"),
        data.get("unloading_point_name"),
        data.get("unloading_point_country"),
        data.get("unloading_point_zip"),
        data.get("unloading_point_city"),
        data.get("pallet_type"),
        quantity, width, length, height,
        loading_meters, volume,
        float(data.get("weight", 0) or 0),
        int(data.get("stackable", False)),
        int(data.get("adr", False)),
        int(data.get("tail_lift", False)),
        int(data.get("insured", False)),
        int(data.get("high_value", False)),
        int(data.get("pre_advise", False)),
        int(data.get("time_slot_loading", False)),
        int(data.get("time_slot_delivery", False)),
        data.get("min_temperature"),
        data.get("max_temperature"),
        int(data.get("temperature_monitoring", False)),
        data.get("required_compartment", "koko kärry"),
        data.get("loading_instructions"),
        data.get("loading_date"),
        data.get("loading_time_start"),
        data.get("loading_time_end"),
        data.get("delivery_date"),
        data.get("delivery_time_start"),
        data.get("delivery_time_end"),
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"message": "Order luotu", "id": new_id, "order_id": order_id}), 201


@app.route("/api/orders/<int:order_id>", methods=["PUT"])
def update_order(order_id):
    conn = get_db_connection()
    order = conn.execute("SELECT trip_id FROM orders WHERE id = ?", (order_id,)).fetchone()

    if not order:
        conn.close()
        return jsonify({"error": "Orderia ei löytynyt"}), 404

    if order["trip_id"]:
        trip = conn.execute(
            "SELECT status FROM trips WHERE id = ?",
            (order["trip_id"],)
        ).fetchone()
        if trip and is_locked(trip["status"]):
            conn.close()
            return jsonify({"error": "Laskutettu keikka on lukittu"}), 403

    data = request.get_json()
    width = float(data.get("pallet_width", 0) or 0)
    length = float(data.get("pallet_length", 0) or 0)
    height = float(data.get("pallet_height", 0) or 0)
    quantity = int(data.get("quantity", 1) or 1)

    loading_meters = calculate_loading_meters(width, length, quantity)
    volume = calculate_volume(width, length, height, quantity)

    conn.execute("""
        UPDATE orders SET
            order_reference=?, pickup_reference=?, goods_description=?, incoterms=?,
            consignor_name=?, consignor_address=?, consignor_country=?,
            consignee_name=?, consignee_address=?, consignee_country=?,
            loading_point_name=?, loading_point_country=?, loading_point_zip=?, loading_point_city=?,
            unloading_point_name=?, unloading_point_country=?, unloading_point_zip=?, unloading_point_city=?,
            pallet_type=?, quantity=?, pallet_width=?, pallet_length=?, pallet_height=?,
            loading_meters=?, volume=?, weight=?,
            stackable=?, adr=?, tail_lift=?, insured=?, high_value=?,
            pre_advise=?, time_slot_loading=?, time_slot_delivery=?,
            min_temperature=?, max_temperature=?, temperature_monitoring=?, required_compartment=?,
            loading_instructions=?,
            loading_date=?, loading_time_start=?, loading_time_end=?,
            delivery_date=?, delivery_time_start=?, delivery_time_end=?
        WHERE id=?
    """, (
        data.get("order_reference"),
        data.get("pickup_reference"),
        data.get("goods_description"),
        data.get("incoterms"),
        data.get("consignor_name"),
        data.get("consignor_address"),
        data.get("consignor_country"),
        data.get("consignee_name"),
        data.get("consignee_address"),
        data.get("consignee_country"),
        data.get("loading_point_name"),
        data.get("loading_point_country"),
        data.get("loading_point_zip"),
        data.get("loading_point_city"),
        data.get("unloading_point_name"),
        data.get("unloading_point_country"),
        data.get("unloading_point_zip"),
        data.get("unloading_point_city"),
        data.get("pallet_type"),
        quantity, width, length, height,
        loading_meters, volume,
        float(data.get("weight", 0) or 0),
        int(data.get("stackable", False)),
        int(data.get("adr", False)),
        int(data.get("tail_lift", False)),
        int(data.get("insured", False)),
        int(data.get("high_value", False)),
        int(data.get("pre_advise", False)),
        int(data.get("time_slot_loading", False)),
        int(data.get("time_slot_delivery", False)),
        data.get("min_temperature"),
        data.get("max_temperature"),
        int(data.get("temperature_monitoring", False)),
        data.get("required_compartment", "koko kärry"),
        data.get("loading_instructions"),
        data.get("loading_date"),
        data.get("loading_time_start"),
        data.get("loading_time_end"),
        data.get("delivery_date"),
        data.get("delivery_time_start"),
        data.get("delivery_time_end"),
        order_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"message": "Order päivitetty"})


@app.route("/api/orders/<int:order_id>", methods=["DELETE"])
def delete_order(order_id):
    conn = get_db_connection()
    order = conn.execute("SELECT trip_id FROM orders WHERE id = ?", (order_id,)).fetchone()

    if not order:
        conn.close()
        return jsonify({"error": "Orderia ei löytynyt"}), 404

    if order["trip_id"]:
        trip = conn.execute(
            "SELECT status FROM trips WHERE id = ?",
            (order["trip_id"],)
        ).fetchone()
        if trip and is_locked(trip["status"]):
            conn.close()
            return jsonify({"error": "Laskutettu keikka on lukittu"}), 403

    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Order poistettu"})


@app.route("/api/trips/<int:trip_id>/orders/<int:order_id>", methods=["POST"])
def add_order_to_trip(trip_id, order_id):
    conn = get_db_connection()
    trip = conn.execute("SELECT status, trailer_type FROM trips WHERE id = ?", (trip_id,)).fetchone()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()

    if not trip:
        conn.close()
        return jsonify({"error": "Keikkaa ei löytynyt"}), 404

    if not order:
        conn.close()
        return jsonify({"error": "Orderia ei löytynyt"}), 404

    if is_locked(trip["status"]):
        conn.close()
        return jsonify({"error": "Laskutettu keikka on lukittu"}), 403

    if order["trip_id"]:
        conn.close()
        return jsonify({"error": "Order on jo lisätty toiselle keikalle"}), 400

    capacity = get_trip_capacity(trip_id, conn)
    specs = TRAILER_SPECS.get(trip["trailer_type"], {})

    new_weight = capacity["total_weight"] + order["weight"]
    new_lm = capacity["total_loading_meters"] + order["loading_meters"]
    new_volume = capacity["total_volume"] + order["volume"]

    warnings = []
    if new_weight > specs.get("max_weight", 24000):
        warnings.append(f"Paino ylittyy: {new_weight} kg / {specs.get('max_weight', 24000)} kg")
    if new_lm > specs.get("max_loading_meters", 13.6):
        warnings.append(f"Lastausmetrit ylittyvät: {new_lm} lm / {specs.get('max_loading_meters', 13.6)} lm")
    if new_volume > specs.get("max_volume", 90):
        warnings.append(f"Tilavuus ylittyy: {new_volume} m³ / {specs.get('max_volume', 90)} m³")

    if warnings:
        conn.close()
        return jsonify({"error": "Kapasiteetti ylittyy", "warnings": warnings}), 400

    conn.execute(
        "UPDATE orders SET trip_id = ?, status = 'Tripillä' WHERE id = ?",
        (trip_id, order_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Order lisätty keikalle"})


@app.route("/api/trips/<int:trip_id>/orders/<int:order_id>", methods=["DELETE"])
def remove_order_from_trip(trip_id, order_id):
    conn = get_db_connection()
    trip = conn.execute("SELECT status FROM trips WHERE id = ?", (trip_id,)).fetchone()

    if not trip:
        conn.close()
        return jsonify({"error": "Keikkaa ei löytynyt"}), 404

    if is_locked(trip["status"]):
        conn.close()
        return jsonify({"error": "Laskutettu keikka on lukittu"}), 403

    conn.execute(
        "UPDATE orders SET trip_id = NULL, status = 'Vapaa' WHERE id = ? AND trip_id = ?",
        (order_id, trip_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Order poistettu keikalta"})


# ===== COSTS =====

@app.route("/api/trips/<int:trip_id>/costs", methods=["GET"])
def get_costs(trip_id):
    conn = get_db_connection()
    costs = conn.execute(
        "SELECT * FROM costs WHERE trip_id = ? ORDER BY cost_code",
        (trip_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(c) for c in costs])


@app.route("/api/trips/<int:trip_id>/costs", methods=["POST"])
def add_cost(trip_id):
    conn = get_db_connection()
    trip = conn.execute("SELECT status, loading_date FROM trips WHERE id = ?", (trip_id,)).fetchone()

    if not trip:
        conn.close()
        return jsonify({"error": "Keikkaa ei löytynyt"}), 404

    if is_locked(trip["status"]):
        conn.close()
        return jsonify({"error": "Laskutettu keikka on lukittu"}), 403

    data = request.get_json()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO costs (trip_id, cost_code, description, amount, cost_type, custom_description)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        trip_id,
        data.get("cost_code"),
        data.get("description"),
        float(data.get("amount", 0)),
        data.get("cost_type", "cost"),
        data.get("custom_description")
    ))
    cost_id = cursor.lastrowid

    fuel_cost_id = None
    if data.get("cost_code") == "120":
        ref_date = trip["loading_date"] or datetime.now().strftime("%Y-%m-%d")
        rate = conn.execute("""
            SELECT multiplier FROM fuel_rates
            WHERE valid_from <= ? AND valid_to >= ?
            ORDER BY valid_from DESC LIMIT 1
        """, (ref_date, ref_date)).fetchone()

        if rate and rate["multiplier"]:
            fuel_amount = round(float(data.get("amount", 0)) * (rate["multiplier"] - 1.0), 2)
            if fuel_amount > 0:
                cursor.execute("""
                    INSERT INTO costs (trip_id, cost_code, description, amount, cost_type)
                    VALUES (?, '200', ?, ?, 'cost')
                """, (trip_id, f"POLTTOAINELISÄ (kerroin {rate['multiplier']})", fuel_amount))
                fuel_cost_id = cursor.lastrowid

    conn.commit()
    response = {"message": "Kulu lisätty", "id": cost_id}
    if fuel_cost_id:
        response["fuel_surcharge_added"] = True
        response["fuel_surcharge_id"] = fuel_cost_id
    conn.close()
    return jsonify(response), 201


@app.route("/api/costs/<int:cost_id>", methods=["PUT"])
def update_cost(cost_id):
    conn = get_db_connection()
    cost = conn.execute("SELECT trip_id FROM costs WHERE id = ?", (cost_id,)).fetchone()

    if not cost:
        conn.close()
        return jsonify({"error": "Kulua ei löytynyt"}), 404

    trip = conn.execute(
        "SELECT status FROM trips WHERE id = ?",
        (cost["trip_id"],)
    ).fetchone()

    if trip and is_locked(trip["status"]):
        conn.close()
        return jsonify({"error": "Laskutettu keikka on lukittu"}), 403

    data = request.get_json()
    conn.execute("""
        UPDATE costs SET cost_code=?, description=?, amount=?, cost_type=?, custom_description=?
        WHERE id=?
    """, (
        data.get("cost_code"),
        data.get("description"),
        float(data.get("amount", 0)),
        data.get("cost_type", "cost"),
        data.get("custom_description"),
        cost_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"message": "Kulu päivitetty"})


@app.route("/api/costs/<int:cost_id>", methods=["DELETE"])
def delete_cost(cost_id):
    conn = get_db_connection()
    cost = conn.execute("SELECT trip_id FROM costs WHERE id = ?", (cost_id,)).fetchone()

    if not cost:
        conn.close()
        return jsonify({"error": "Kulua ei löytynyt"}), 404

    trip = conn.execute(
        "SELECT status FROM trips WHERE id = ?",
        (cost["trip_id"],)
    ).fetchone()

    if trip and is_locked(trip["status"]):
        conn.close()
        return jsonify({"error": "Laskutettu keikka on lukittu"}), 403

    conn.execute("DELETE FROM costs WHERE id = ?", (cost_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Kulu poistettu"})


# ===== DASHBOARD =====

@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    conn = get_db_connection()

    trips = conn.execute("""
        SELECT t.id, t.trip_id, t.status, t.loading_date, t.delivery_date,
               t.first_pickup_city, t.first_pickup_country,
               t.trip_end_city, t.trip_end_country,
               c.name as carrier_name,
               COUNT(DISTINCT o.id) as order_count,
               COALESCE(SUM(CASE WHEN co.cost_type='revenue' THEN co.amount ELSE 0 END), 0) as total_revenue,
               COALESCE(SUM(CASE WHEN co.cost_type='cost' THEN co.amount ELSE 0 END), 0) as total_costs
        FROM trips t
        LEFT JOIN carriers c ON t.carrier_id = c.id
        LEFT JOIN orders o ON o.trip_id = t.id
        LEFT JOIN costs co ON co.trip_id = t.id
        GROUP BY t.id
        ORDER BY t.created_at DESC
        LIMIT 20
    """).fetchall()

    kpi = conn.execute("""
        SELECT
            COUNT(DISTINCT t.id) as total_trips,
            COUNT(DISTINCT o.id) as total_orders,
            COALESCE(SUM(CASE WHEN co.cost_type='revenue' THEN co.amount ELSE 0 END), 0) as total_revenue,
            COALESCE(SUM(CASE WHEN co.cost_type='cost' THEN co.amount ELSE 0 END), 0) as total_costs
        FROM trips t
        LEFT JOIN orders o ON o.trip_id = t.id
        LEFT JOIN costs co ON co.trip_id = t.id
    """).fetchone()

    status_counts = conn.execute("""
        SELECT status, COUNT(*) as count FROM trips GROUP BY status
    """).fetchall()

    conn.close()

    trips_list = []
    for t in trips:
        d = dict(t)
        revenue = d["total_revenue"]
        costs = d["total_costs"]
        margin = round(revenue - costs, 2)
        d["margin"] = margin
        d["margin_percent"] = round(margin / revenue * 100, 2) if revenue > 0 else 0
        d["total_revenue"] = round(revenue, 2)
        d["total_costs"] = round(costs, 2)
        trips_list.append(d)

    kpi_dict = dict(kpi)
    total_revenue = kpi_dict["total_revenue"]
    total_costs = kpi_dict["total_costs"]
    kpi_dict["margin"] = round(total_revenue - total_costs, 2)
    kpi_dict["margin_percent"] = round(
        (kpi_dict["margin"] / total_revenue * 100), 2
    ) if total_revenue > 0 else 0

    return jsonify({
        "kpi": kpi_dict,
        "trips": trips_list,
        "status_counts": [dict(s) for s in status_counts]
    })


# ===== CUSTOMERS =====

@app.route("/api/customers", methods=["GET"])
def get_customers():
    conn = get_db_connection()
    customers = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(c) for c in customers])


@app.route("/api/customers/<int:customer_id>", methods=["GET"])
def get_customer(customer_id):
    conn = get_db_connection()
    customer = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    conn.close()
    if not customer:
        return jsonify({"error": "Asiakasta ei löytynyt"}), 404
    return jsonify(dict(customer))


@app.route("/api/customers", methods=["POST"])
def create_customer():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Nimi on pakollinen"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO customers (name, business_id, address, zip, city, country, contact_person, phone, email, customer_type, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("name"),
        data.get("business_id"),
        data.get("address"),
        data.get("zip"),
        data.get("city"),
        data.get("country", "FI"),
        data.get("contact_person"),
        data.get("phone"),
        data.get("email"),
        data.get("customer_type", "molemmat"),
        data.get("notes"),
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"message": "Asiakas luotu", "id": new_id}), 201


@app.route("/api/customers/<int:customer_id>", methods=["PUT"])
def update_customer(customer_id):
    conn = get_db_connection()
    customer = conn.execute("SELECT id FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if not customer:
        conn.close()
        return jsonify({"error": "Asiakasta ei löytynyt"}), 404

    data = request.get_json()
    conn.execute("""
        UPDATE customers SET
            name=?, business_id=?, address=?, zip=?, city=?, country=?,
            contact_person=?, phone=?, email=?, customer_type=?, notes=?
        WHERE id=?
    """, (
        data.get("name"),
        data.get("business_id"),
        data.get("address"),
        data.get("zip"),
        data.get("city"),
        data.get("country", "FI"),
        data.get("contact_person"),
        data.get("phone"),
        data.get("email"),
        data.get("customer_type", "molemmat"),
        data.get("notes"),
        customer_id,
    ))
    conn.commit()
    conn.close()
    return jsonify({"message": "Asiakas päivitetty"})


@app.route("/api/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    conn = get_db_connection()
    customer = conn.execute("SELECT id FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if not customer:
        conn.close()
        return jsonify({"error": "Asiakasta ei löytynyt"}), 404

    conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Asiakas poistettu"})


# ===== FUEL RATES =====

@app.route("/api/fuel-rates", methods=["GET"])
def get_fuel_rates():
    conn = get_db_connection()
    rates = conn.execute("SELECT * FROM fuel_rates ORDER BY valid_from DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rates])


@app.route("/api/fuel-rates/current", methods=["GET"])
def get_current_fuel_rate():
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    conn = get_db_connection()
    rate = conn.execute("""
        SELECT * FROM fuel_rates
        WHERE valid_from <= ? AND valid_to >= ?
        ORDER BY valid_from DESC LIMIT 1
    """, (date_str, date_str)).fetchone()
    conn.close()
    if rate:
        return jsonify(dict(rate))
    return jsonify({"multiplier": None, "message": "Ei voimassaolevaa kerrointa"}), 404


@app.route("/api/fuel-rates", methods=["POST"])
def create_fuel_rate():
    data = request.get_json()
    if not data or not data.get("valid_from") or not data.get("valid_to") or not data.get("multiplier"):
        return jsonify({"error": "valid_from, valid_to ja multiplier ovat pakollisia"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO fuel_rates (valid_from, valid_to, multiplier) VALUES (?, ?, ?)
    """, (data["valid_from"], data["valid_to"], float(data["multiplier"])))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"message": "Kerroin lisätty", "id": new_id}), 201


@app.route("/api/fuel-rates/<int:rate_id>", methods=["PUT"])
def update_fuel_rate(rate_id):
    conn = get_db_connection()
    if not conn.execute("SELECT id FROM fuel_rates WHERE id=?", (rate_id,)).fetchone():
        conn.close()
        return jsonify({"error": "Kerrointa ei löydy"}), 404
    data = request.get_json()
    conn.execute("""
        UPDATE fuel_rates SET valid_from=?, valid_to=?, multiplier=? WHERE id=?
    """, (data["valid_from"], data["valid_to"], float(data["multiplier"]), rate_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Kerroin päivitetty"})


@app.route("/api/fuel-rates/<int:rate_id>", methods=["DELETE"])
def delete_fuel_rate(rate_id):
    conn = get_db_connection()
    if not conn.execute("SELECT id FROM fuel_rates WHERE id=?", (rate_id,)).fetchone():
        conn.close()
        return jsonify({"error": "Kerrointa ei löydy"}), 404
    conn.execute("DELETE FROM fuel_rates WHERE id=?", (rate_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Kerroin poistettu"})


@app.route("/api/costs-dashboard", methods=["GET"])
def get_costs_dashboard():
    from_date = request.args.get("from")
    to_date   = request.args.get("to")
    conn = get_db_connection()

    # Kulukoodien kategoriaryhmät
    CATEGORY_CODES = {
        "lautta":    ["500", "510"],
        "rahti":     ["100", "120", "200", "210", "220"],
        "tiemaksut": ["300", "310"],
        "kalusto":   ["400", "401", "410", "830", "831"],
        "lisat":     ["600", "610", "700", "799", "800", "810", "820"],
    }

    # WHERE-ehto loading_date-suodatukselle
    date_filter = ""
    params = []
    if from_date and to_date:
        date_filter = "WHERE t.loading_date BETWEEN ? AND ?"
        params = [from_date, to_date]

    trips_raw = conn.execute(f"""
        SELECT
            t.id, t.trip_id, t.status,
            t.first_pickup_city, t.first_pickup_country,
            t.trip_end_city, t.trip_end_country,
            t.loading_date,
            c.name AS carrier_name,
            COALESCE(SUM(CASE WHEN co.cost_type='revenue' THEN co.amount ELSE 0 END),0) AS revenue,
            COALESCE(SUM(CASE WHEN co.cost_type='cost'    THEN co.amount ELSE 0 END),0) AS costs
        FROM trips t
        LEFT JOIN carriers c  ON t.carrier_id = c.id
        LEFT JOIN costs   co  ON t.id = co.trip_id
        {date_filter}
        GROUP BY t.id
        ORDER BY t.loading_date DESC NULLS LAST, t.id DESC
    """, params).fetchall()

    trip_list = []
    for t in trips_raw:
        rev    = t["revenue"] or 0
        osto   = t["costs"]   or 0
        margin = rev - osto
        pct    = round(margin / rev * 100, 1) if rev > 0 else 0.0
        start  = f"{t['first_pickup_country'] or ''} {t['first_pickup_city'] or '—'}".strip()
        end    = f"{t['trip_end_country'] or ''} {t['trip_end_city'] or '—'}".strip()
        trip_list.append({
            "id": t["id"],
            "trip_id": t["trip_id"],
            "status": t["status"],
            "route": f"{start} → {end}",
            "carrier_name": t["carrier_name"] or "—",
            "loading_date": t["loading_date"],
            "revenue": round(rev, 2),
            "costs":   round(osto, 2),
            "margin":  round(margin, 2),
            "margin_pct": pct,
        })

    # KPI-summat
    total_rev    = sum(r["revenue"] for r in trip_list)
    total_costs  = sum(r["costs"]   for r in trip_list)
    total_margin = total_rev - total_costs
    total_pct    = round(total_margin / total_rev * 100, 1) if total_rev > 0 else 0.0

    # Kategoriasummat
    categories = {}
    for cat_key, codes in CATEGORY_CODES.items():
        ph = ",".join("?" * len(codes))
        row = conn.execute(f"""
            SELECT
                COALESCE(SUM(CASE WHEN co.cost_type='cost'    THEN co.amount ELSE 0 END),0) AS osto,
                COALESCE(SUM(CASE WHEN co.cost_type='revenue' THEN co.amount ELSE 0 END),0) AS myynti
            FROM costs co
            JOIN trips t ON co.trip_id = t.id
            WHERE co.cost_code IN ({ph})
            {"AND t.loading_date BETWEEN ? AND ?" if date_filter else ""}
        """, (*codes, *params)).fetchone()
        categories[cat_key] = {
            "osto":   round(row["osto"]   or 0, 2),
            "myynti": round(row["myynti"] or 0, 2),
        }

    conn.close()
    return jsonify({
        "kpi": {
            "revenue":     round(total_rev, 2),
            "costs":       round(total_costs, 2),
            "margin":      round(total_margin, 2),
            "margin_pct":  total_pct,
            "trip_count":  len(trip_list),
        },
        "trips":      trip_list,
        "categories": categories,
    })


if __name__ == "__main__":
    app.run(debug=True)
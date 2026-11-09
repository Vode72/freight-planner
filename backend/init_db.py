import sqlite3
from datetime import date, timedelta

import money
from db_migrate import upgrade_connection


def create_schema(conn):
    """Luo tai päivittää skeeman Alembic-migraatioilla (alembic upgrade head).

    Skeeman ainoa lähde ovat migrations/versions-revisiot. Toimii myös
    muistikantaan ja olemassa olevaan kantaan.
    """
    upgrade_connection(conn)


def seed_demo_data(conn):
    """Koko demodata: perusdata + viitedemodata. create_schema() ajettu ensin."""
    seed_base_demo(conn)
    seed_reference_demo(conn)


def seed_reference_demo(conn):
    """Demodata, jonka vanhat migrate_*.py-skriptit lisäsivät: maarajoitukset,
    terminaalit, huollot, km- ja lauttahinnat, lisähinnat (+ polttoainelisän
    siirto fuel_rates-taulusta) ja asiakashinnasto. Ei commitoi."""
    from surcharges import seed_surcharge_rates, migrate_fuel_rates
    from customer_pricing import seed_customer_pricing
    cursor = conn.cursor()
    _seed_restrictions_demo(cursor)
    _seed_hallinta_demo(cursor)
    seed_surcharge_rates(conn)
    migrate_fuel_rates(conn)
    seed_customer_pricing(conn)


def _seed_restrictions_demo(cursor):
    cursor.execute("DELETE FROM country_restrictions")
    restrictions = [
        ("CH", "SUNDAY_BAN",  "sun", None,    None,    "00:00", "24:00", 3.5,  "Sunnuntaikielto — ei poikkeuksia", "red",    "Ei poikkeuksia"),
        ("CH", "NIGHT_BAN",   "all", None,    None,    "22:00", "05:00", 3.5,  "Yöajokielto joka yö",              "red",    None),
        ("CH", "WEIGHT_LIMIT","all", None,    None,    None,    None,    40.0, "Max GVW 40t (EU 44t ei kelpaa)",   "red",    None),
        ("DE", "SUNDAY_BAN",  "sun", None,    None,    "00:00", "22:00", 7.5,  "Sunnuntaikielto",                  "orange", None),
        ("DE", "SUMMER_BAN",  "sat", "07-01", "08-31", "00:00", "22:00", 7.5,  "Kesälauantairajoitus heinä-elokuu","yellow", "Tietyt päätiet"),
        ("AT", "SUNDAY_BAN",  "sun", None,    None,    "00:00", "22:00", 7.5,  "Sunnuntaikielto",                  "orange", None),
        ("AT", "NIGHT_BAN",   "all", "11-01", "03-31", "22:00", "05:00", 7.5,  "Brenner-reitin yökielto talvikaudella", "orange", None),
        ("FR", "SUNDAY_BAN",  "sun", None,    None,    "00:00", "22:00", 7.5,  "Sunnuntaikielto",                  "orange", None),
        ("IT", "SUNDAY_BAN",  "sun", None,    None,    "07:00", "22:00", 7.5,  "Sunnuntaikielto",                  "orange", None),
        ("IT", "SUMMER_BAN",  "sat", "06-01", "09-30", "08:00", "16:00", 7.5,  "Kesälauantairajoitus",             "yellow", None),
        ("IT", "WEIGHT_LIMIT","all", None,    None,    None,    None,    44.0, "Max GVW 44t",                      "orange", None),
        ("PL", "SUNDAY_BAN",  "sun", None,    None,    "08:00", "22:00", 12.0, "Sunnuntaikielto",                  "orange", None),
        ("CZ", "SUNDAY_BAN",  "sun", None,    None,    "13:00", "22:00", 7.5,  "Sunnuntaikielto",                  "yellow", None),
        ("SK", "SUNDAY_BAN",  "sun", None,    None,    "00:00", "22:00", 7.5,  "Sunnuntaikielto",                  "orange", None),
        ("LU", "SUNDAY_BAN",  "sun", None,    None,    "00:00", "21:45", 7.5,  "Sunnuntaikielto",                  "orange", None),
    ]
    cursor.executemany("""
        INSERT INTO country_restrictions
            (country_code, restriction_type, day_of_week, date_from, date_to,
             time_from, time_to, min_weight_t, description, severity, exemptions)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, restrictions)

    cursor.execute("DELETE FROM terminals")
    terminals = [
        ("Demo Terminal Helsinki",   "FI", "Helsinki",  "Vuosaarentie 10, 00980 Helsinki"),
        ("Demo Terminal Tampere",    "FI", "Tampere",   "Naistenlahdenranta 4, 33200 Tampere"),
        ("Demo Terminal Antwerpen",  "BE", "Antwerpen", "Havenstraat 12, 2030 Antwerpen"),
        ("Demo Terminal Bruxelles",  "BE", "Bruxelles", "Rue du Port 8, 1000 Bruxelles"),
        ("Demo Terminal Rotterdam",  "NL", "Rotterdam", "Waalhaven 34, 3087 Rotterdam"),
        ("Demo Terminal Amsterdam",  "NL", "Amsterdam", "Westpoort 17, 1048 Amsterdam"),
        ("Demo Terminal Hamburg",    "DE", "Hamburg",   "Hafenweg 22, 20457 Hamburg"),
        ("Demo Terminal Frankfurt",  "DE", "Frankfurt", "Industriestr. 45, 60327 Frankfurt am Main"),
        ("Demo Terminal Paris",      "FR", "Rungis",    "Rue de la Logistique 5, 94150 Rungis"),
        ("Demo Terminal Lyon",       "FR", "Lyon",      "Avenue du Port 18, 69007 Lyon"),
        ("Demo Terminal Zürich",     "CH", "Zürich",    "Industriestrasse 8, 8005 Zürich"),
        ("Demo Terminal Basel",      "CH", "Basel",     "Rheinweg 14, 4058 Basel"),
        ("Demo Terminal Wien",       "AT", "Wien",      "Laxenburger Str. 20, 1100 Wien"),
        ("Demo Terminal Innsbruck",  "AT", "Innsbruck", "Innsbrucker Str. 3, 6020 Innsbruck"),
        ("Demo Terminal Milano",     "IT", "Milano",    "Via della Logistica 9, 20142 Milano"),
        ("Demo Terminal Roma",       "IT", "Roma",      "Via Portuense 33, 00148 Roma"),
    ]
    cursor.executemany(
        "INSERT INTO terminals (name, country_code, city, address) VALUES (?,?,?,?)",
        terminals,
    )


def _seed_hallinta_demo(cursor):
    trailers = cursor.execute("SELECT plate_number, trailer_type FROM trailers").fetchall()
    trailer_map = {t[0]: t[1] for t in trailers}

    cursor.execute("DELETE FROM trailer_maintenance")

    today = date.today()
    maintenance_rows = []

    for plate, days_ago, next_days in [
        ("URV-001", 365, 365),
        ("URV-002", 180, 545),
        ("SRV-001", 270, 460),
        ("CRT-001", 90, 640),
        ("HRV-001", 400, 330),
    ]:
        if plate in trailer_map:
            maintenance_rows.append((
                plate, "INSPECTION",
                (today - timedelta(days=days_ago)).isoformat(),
                (today + timedelta(days=next_days - days_ago)).isoformat(),
                "Katsastus OK",
            ))

    for plate, days_ago, next_days in [
        ("URV-001", 120, 180),
        ("URV-002", 30, 150),
        ("TRV-001", 200, -20),
    ]:
        ttype = trailer_map.get(plate, "")
        if "Umpikaappi" in ttype:
            maintenance_rows.append((
                plate, "REFRIGERATION",
                (today - timedelta(days=days_ago)).isoformat(),
                (today + timedelta(days=next_days)).isoformat(),
                "Kylmäkonehuolto suoritettu",
            ))

    cursor.executemany(
        "INSERT INTO trailer_maintenance (trailer_id, maintenance_type, date, next_due, notes) "
        "VALUES (?,?,?,?,?)",
        maintenance_rows,
    )

    if "HRV-001" in trailer_map:
        cursor.execute(
            "UPDATE trailers SET inspection_date='2025-05-01', inspection_due=? WHERE plate_number='HRV-001'",
            ((today - timedelta(days=20)).isoformat(),),
        )
    for plate, insp_date, delta in [
        ("URV-003", "2025-11-01", 18),
        ("CRT-002", "2025-11-15", 25),
        ("URV-001", "2025-06-01", 365 - 120),
        ("URV-002", "2025-12-01", 180),
        ("SRV-001", "2025-08-01", 90),
        ("CRT-001", "2026-01-15", 120),
    ]:
        if plate in trailer_map:
            cursor.execute(
                f"UPDATE trailers SET inspection_date=?, inspection_due=? WHERE plate_number=?",
                (insp_date, (today + timedelta(days=delta)).isoformat(), plate),
            )

    for plate, svc_date, delta, interval in [
        ("URV-001", "2025-12-01", 60, 6),
        ("URV-002", "2026-01-15", 15, 6),
        ("TRV-001", "2025-10-01", -20, 6),
        ("TRV-002", "2026-02-01", 95, 6),
    ]:
        if plate in trailer_map:
            cursor.execute(
                "UPDATE trailers SET refrigeration_service_date=?, refrigeration_service_due=?, "
                "refrigeration_service_interval_months=? WHERE plate_number=?",
                (svc_date, (today + timedelta(days=delta)).isoformat(), interval, plate),
            )

    cursor.execute("DELETE FROM km_rates")
    cursor.execute(
        "INSERT INTO km_rates (valid_from, valid_to, domestic_rate_e4, continent_rate_e4, notes) "
        "VALUES ('2026-01-01', NULL, ?, ?, 'Perushinnoittelu 2026')",
        (money.to_e4("1.85"), money.to_e4("2.20")),
    )

    cursor.execute("DELETE FROM ferry_rates")
    ferry_routes = [
        ("Helsinki - Travemünde", 1050, "2026-01-01", None),
        ("Hanko - Lübeck",        1010, "2026-01-01", None),
        ("Hanko - Rostock",        750, "2026-01-01", None),
        ("Kotka - Antwerpen",     1800, "2026-01-01", None),
    ]
    cursor.executemany(
        "INSERT INTO ferry_rates (route, price_cents, valid_from, valid_to) VALUES (?,?,?,?)",
        [(route, money.to_cents(price), vf, vt) for route, price, vf, vt in ferry_routes],
    )


def seed_base_demo(conn):
    """Perusdemodata: trailerit, kuljettajat, asiakkaat, tripit, orderit, kulut."""
    cursor = conn.cursor()

    trailers = [
        ("URV-001", "FB-2401", "Umpikaappi", 42, 65),
        ("URV-002", "FB-2402", "Umpikaappi", 42, 65),
        ("URV-003", "FB-2403", "Umpikaappi", 42, 65),
        ("SRV-001", "FS-2301", "Sivuaukeava", 45, 70),
        ("SRV-002", "FS-2302", "Sivuaukeava", 45, 70),
        ("TRV-001", "FD-1801", "Umpikaappi 2-koneinen", 43, 67),
        ("TRV-002", "FD-1802", "Umpikaappi 2-koneinen", 43, 67),
        ("CRT-001", "CT-3201", "Pressutrailer", 35, 54),
        ("CRT-002", "CT-3202", "Pressutrailer", 35, 54),
        ("CRT-003", "CT-3203", "Pressutrailer", 35, 54),
        ("HRV-001", "CM-4101", "Megatrailer", 38, 59),
        ("HRV-002", "CM-4102", "Megatrailer", 38, 59),
    ]
    # leasing_rate / rental_rate €/pv → sentteinä
    cursor.executemany(
        "INSERT INTO trailers (plate_number, identifier, trailer_type, "
        "leasing_rate_cents, rental_rate_cents) VALUES (?, ?, ?, ?, ?)",
        [(plate, ident, ttype, money.to_cents(leasing), money.to_cents(rental))
         for plate, ident, ttype, leasing, rental in trailers],
    )

    carriers = [
        ("Demo Kuljetus Helsinki Oy", "FI", "Helsinki", "9990101-1", "Matti Virtanen", "+358 40 123 4567"),
        ("Demo Road Turku Oy", "FI", "Turku", "9990102-2", "Juha Mäkinen", "+358 40 234 5678"),
        ("Pohjois-Demo Kuljetus Oy", "FI", "Oulu", "9990103-3", "Pekka Korhonen", "+358 40 345 6789"),
        ("Demo Trans GmbH", "DE", "Hamburg", "DE999000101", "Hans Mueller", "+49 40 123 4567"),
        ("Demo Cargo BV", "NL", "Rotterdam", "NL999000102", "Jan van Berg", "+31 10 123 4567"),
        ("Demo Logistics AB", "SE", "Göteborg", "SE999000103", "Erik Svensson", "+46 31 123 4567"),
    ]
    cursor.executemany(
        "INSERT INTO carriers (name, country, city, business_id, contact_person, phone) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        carriers,
    )

    trucks = [
        ("NRF-001", 1), ("NRF-002", 1),
        ("BLR-001", 2), ("BLR-002", 2),
        ("PHK-001", 3), ("PHK-002", 3),
        ("ETR-001", 4), ("ETR-002", 4),
        ("CTC-001", 5), ("CTC-002", 5),
        ("SCL-001", 6), ("SCL-002", 6),
    ]
    cursor.executemany(
        "INSERT INTO trucks (plate_number, carrier_id) VALUES (?, ?)",
        trucks,
    )

    customers = [
        ("Demo Retail Finland Oy", "9990201-1", "Demosatama 5", "00160", "Helsinki", "FI",
         "Antti Leinonen", "+358 40 111 2222", "antti.leinonen@retail.example.com", "consignor", None),
        ("Demo Rakennustarvike Oy", "9990202-2", "Demotehtaantie 3", "04200", "Kerava", "FI",
         "Satu Niemi", "+358 40 222 3333", "satu.niemi@rakennus.example.com", "molemmat", None),
        ("Demo Päivittäistavara Oy", "9990203-3", "Demovarastontie 34", "00510", "Helsinki", "FI",
         "Ville Hakala", "+358 40 333 4444", "ville.hakala@ptk.example.com", "consignor", None),
        ("Demo Machinery Finland Oy", "9990204-4", "Demokonekatu 5", "00180", "Helsinki", "FI",
         "Laura Heikkinen", "+358 40 444 5555", "laura.heikkinen@machinery.example.com", "consignor", None),
        ("Baltic Demo Foods Oy", "9990205-5", "Demotukuntie 6", "00580", "Helsinki", "FI",
         "Mikko Järvinen", "+358 40 555 6666", "mikko.jarvinen@foods.example.com", "molemmat", None),
        ("Demo Cranes Oy", "9990206-6", "Demonosturintie 8", "05830", "Hyvinkää", "FI",
         "Erika Lund", "+358 40 666 7777", "erika.lund@cranes.example.com", "consignor", None),
        ("Demo Shipyard Turku Oy", "9990207-7", "Demotelakantie 1", "20810", "Turku", "FI",
         "Timo Rantanen", "+358 40 777 8888", "timo.rantanen@shipyard.example.com", "molemmat", None),
        ("Demo Paper Oy", "9990208-8", "Demopaperitie 1", "00100", "Helsinki", "FI",
         "Minna Saarinen", "+358 40 888 9999", "minna.saarinen@paper.example.com", "consignor", None),
    ]
    cursor.executemany(
        "INSERT INTO customers (name, business_id, address, zip, city, country, "
        "contact_person, phone, email, customer_type, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        customers,
    )

    fuel_rates_demo = [
        ("2026-01-01", "2026-01-31", 1.15),
        ("2026-02-01", "2026-02-28", 1.16),
        ("2026-03-01", "2026-03-31", 1.18),
        ("2026-04-01", "2026-04-30", 1.17),
        ("2026-05-01", "2026-05-31", 1.19),
    ]
    cursor.executemany(
        "INSERT INTO fuel_rates (valid_from, valid_to, multiplier) VALUES (?, ?, ?)",
        fuel_rates_demo,
    )

    trips_demo = [
        ("TRP-2026-001", "Suunniteltu",
         "FI", "00160", "Helsinki", "DE", "20537", "Hamburg", "Suora",
         1, 1, "Umpikaappi", "NRF-001",
         "2026-05-14", "07:00", "09:00", "2026-05-16", "08:00", "12:00",
         None, None, None, 0, 0, 0, 0),
        ("TRP-2026-002", "Vahvistettu",
         "FI", "20100", "Turku", "SE", "11120", "Stockholm", "Lautta",
         6, 4, "Sivuaukeava", "SCL-001",
         "2026-05-12", "06:00", "08:00", "2026-05-13", "14:00", "16:00",
         "Turku-Stockholm", "2026-05-12 20:00", "2026-05-13 09:00", 0, 0, 0, 0),
        ("TRP-2026-003", "Käynnissä",
         "FI", "00160", "Helsinki", "NL", "3013", "Rotterdam", "Suora",
         2, 8, "Pressutrailer", "BLR-001",
         "2026-05-08", "07:00", "09:00", "2026-05-12", "10:00", "14:00",
         None, None, None, 0, 0, 0, 0),
        ("TRP-2026-004", "Toimitettu",
         "FI", "90100", "Oulu", "DE", "60329", "Frankfurt", "Suora",
         4, 6, "Umpikaappi 2-koneinen", "ETR-001",
         "2026-05-02", "07:00", "10:00", "2026-05-05", "09:00", "13:00",
         None, None, None, 0, 0, 0, 1),
        ("TRP-2026-005", "Laskutettu",
         "FI", "00160", "Helsinki", "EE", "10111", "Tallinn", "Lautta",
         1, 2, "Umpikaappi", "NRF-002",
         "2026-04-28", "08:00", "10:00", "2026-04-29", "12:00", "15:00",
         "Helsinki-Tallinn", "2026-04-28 20:00", "2026-04-29 07:00", 0, 0, 0, 0),
        ("TRP-2026-006", "Vahvistettu",
         "FI", "33100", "Tampere", "PL", "00-001", "Varsova", "Suora",
         3, 11, "Megatrailer", "PHK-001",
         "2026-05-15", "06:00", "09:00", "2026-05-19", "10:00", "14:00",
         None, None, None, 0, 0, 0, 0),
        ("TRP-2026-007", "Suunniteltu",
         "FI", "02100", "Espoo", "NO", "0150", "Oslo", "Suora",
         2, 5, "Sivuaukeava", "BLR-002",
         "2026-05-20", "07:00", "09:00", "2026-05-22", "10:00", "14:00",
         None, None, None, 0, 0, 0, 0),
    ]

    trip_db_ids = []
    for t in trips_demo:
        cursor.execute("""
            INSERT INTO trips (trip_id, status,
                first_pickup_country, first_pickup_zip, first_pickup_city,
                trip_end_country, trip_end_zip, trip_end_city, transport_type,
                carrier_id, trailer_id, trailer_type, truck_plate,
                loading_date, loading_time_start, loading_time_end,
                delivery_date, delivery_time_start, delivery_time_end,
                ferry_route, ferry_departure, ferry_arrival,
                adr, tail_lift, temperature_controlled, fixed_delivery_date)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, t)
        trip_db_ids.append(cursor.lastrowid)

    orders_demo = [
        ("ORD-2026-001", trip_db_ids[0], "Tilattu", "DCR-2026-1401",
         "Nosturikomponentit", "DAP",
         "Demo Cranes Oy", "Demonosturintie 8, 05830 Hyvinkää", "FI",
         "Demo Stahl AG", "Demostahlstr. 10, 47259 Duisburg", "DE",
         "Demo Cranes Oy", "FI", "05830", "Hyvinkää",
         "Demo Stahl AG", "DE", "47259", "Duisburg",
         "EUR", 12, 5.4, 42.5, 8200, "2026-05-14", "2026-05-16"),
        ("ORD-2026-002", trip_db_ids[0], "Tilattu", "DPA-2026-0514",
         "Paperi", "DAP",
         "Demo Paper Oy", "Demopaperitie 1, 00100 Helsinki", "FI",
         "Demo Karton GmbH", "Demokartonweg 6, 47800 Krefeld", "DE",
         "Demo Paper Oy", "FI", "00100", "Helsinki",
         "Demo Karton GmbH", "DE", "47800", "Krefeld",
         "EUR", 18, 3.8, 28.6, 6400, "2026-05-14", "2026-05-16"),
        ("ORD-2026-003", trip_db_ids[1], "Tilattu", "BDF-2026-0512",
         "Elintarvikkeet", "DAP",
         "Baltic Demo Foods Oy", "Demotukuntie 6, 00580 Helsinki", "FI",
         "Demo Livs AB", "Demovägen 3, 11927 Stockholm", "SE",
         "Baltic Demo Foods Oy", "FI", "20810", "Turku",
         "Demo Livs AB", "SE", "11927", "Stockholm",
         "EUR", 32, 8.0, 62.4, 12000, "2026-05-12", "2026-05-13"),
        ("ORD-2026-004", trip_db_ids[2], "Käynnissä", "DRF-2026-0508",
         "Teollisuuskemikaalit", "CPT",
         "Demo Retail Finland Oy", "Demosatama 5, 00160 Helsinki", "FI",
         "Demo Chemicals NV", "Demohandelstraat 87, 3013 Rotterdam", "NL",
         "Demo Retail Finland Oy", "FI", "00160", "Helsinki",
         "Demo Chemicals NV", "NL", "3013", "Rotterdam",
         "EUR", 22, 6.8, 51.2, 9500, "2026-05-08", "2026-05-12"),
        ("ORD-2026-005", trip_db_ids[2], "Käynnissä", "DRT-2026-0508",
         "Rakennustarvikkeet", "DAP",
         "Demo Rakennustarvike Oy", "Demotehtaantie 3, 04200 Kerava", "FI",
         "Demo Bouwmarkt BV", "Demoweg 45, 2700 Zoetermeer", "NL",
         "Demo Rakennustarvike Oy", "FI", "04200", "Kerava",
         "Demo Bouwmarkt BV", "NL", "2700", "Zoetermeer",
         "FIN", 16, 5.2, 38.4, 11200, "2026-05-08", "2026-05-12"),
        ("ORD-2026-006", trip_db_ids[2], "Käynnissä", "DST-2026-0508",
         "Laivaosat", "EXW",
         "Demo Shipyard Turku Oy", "Demotelakantie 1, 20810 Turku", "FI",
         "Demo Scheepswerf BV", "Demohaven 20, 4200 Gorinchem", "NL",
         "Demo Shipyard Turku Oy", "FI", "20810", "Turku",
         "Demo Scheepswerf BV", "NL", "4200", "Gorinchem",
         "EUR", 10, 3.5, 26.5, 4800, "2026-05-08", "2026-05-12"),
        ("ORD-2026-007", trip_db_ids[3], "Toimitettu", "DPA-2026-0502",
         "Paperirullat", "DAP",
         "Demo Paper Oy", "Demopaperitie 1, 00100 Helsinki", "FI",
         "Demo Papier GmbH", "Demopapierstr. 15, 60329 Frankfurt", "DE",
         "Demo Paper Oy", "FI", "00100", "Helsinki",
         "Demo Papier GmbH", "DE", "60329", "Frankfurt",
         "EUR", 24, 7.6, 56.8, 14000, "2026-05-02", "2026-05-05"),
        ("ORD-2026-008", trip_db_ids[3], "Toimitettu", "DCR-2026-0502",
         "Nosturiosat", "CPT",
         "Demo Cranes Oy", "Demonosturintie 8, 05830 Hyvinkää", "FI",
         "Demo Kranbau GmbH", "Demokranstr. 28, 58300 Wetter", "DE",
         "Demo Cranes Oy", "FI", "05830", "Hyvinkää",
         "Demo Kranbau GmbH", "DE", "58300", "Wetter",
         "EUR", 14, 4.8, 36.0, 7300, "2026-05-02", "2026-05-05"),
        ("ORD-2026-009", trip_db_ids[4], "Toimitettu", "DPT-2026-0428",
         "Päivittäistavarat", "DAP",
         "Demo Päivittäistavara Oy", "Demovarastontie 34, 00510 Helsinki", "FI",
         "Demo Kaubandus AS", "Demo tee 2, 10111 Tallinn", "EE",
         "Demo Päivittäistavara Oy", "FI", "00510", "Helsinki",
         "Demo Kaubandus AS", "EE", "10111", "Tallinn",
         "EUR", 42, 10.4, 81.6, 16500, "2026-04-28", "2026-04-29"),
        ("ORD-2026-010", trip_db_ids[5], "Tilattu", "BDF-2026-0515",
         "Pakkausmateriaalit", "DAP",
         "Baltic Demo Foods Oy", "Demotukuntie 6, 00580 Helsinki", "FI",
         "Demo Budowa Sp. z o.o.", "ul. Demowa 92, 00-807 Warszawa", "PL",
         "Baltic Demo Foods Oy", "FI", "00580", "Helsinki",
         "Demo Budowa Sp. z o.o.", "PL", "00-807", "Varsova",
         "EUR", 18, 6.5, 50.7, 7200, "2026-05-15", "2026-05-19"),
        ("ORD-2026-011", trip_db_ids[5], "Tilattu", "DMF-2026-0515",
         "Koneenvaraosat", "CPT",
         "Demo Machinery Finland Oy", "Demokonekatu 5, 00180 Helsinki", "FI",
         "Demo Maszyny SA", "ul. Demowa 51, 40-698 Katowice", "PL",
         "Demo Machinery Finland Oy", "FI", "00180", "Helsinki",
         "Demo Maszyny SA", "PL", "40-698", "Katowice",
         "EUR", 14, 4.2, 31.5, 5800, "2026-05-15", "2026-05-19"),
        ("ORD-2026-012", trip_db_ids[6], "Tilattu", "DRF-2026-0520",
         "Päivittäistavaroita", "DAP",
         "Demo Retail Finland Oy", "Demosatama 5, 00160 Helsinki", "FI",
         "Demo Dagligvare AS", "Demogata 8, 0150 Oslo", "NO",
         "Demo Retail Finland Oy", "FI", "00160", "Helsinki",
         "Demo Dagligvare AS", "NO", "0150", "Oslo",
         "EUR", 36, 9.2, 71.5, 13800, "2026-05-20", "2026-05-22"),
    ]
    cursor.executemany("""
        INSERT INTO orders (order_id, trip_id, status, order_reference,
            goods_description, incoterms,
            consignor_name, consignor_address, consignor_country,
            consignee_name, consignee_address, consignee_country,
            loading_point_name, loading_point_country, loading_point_zip, loading_point_city,
            unloading_point_name, unloading_point_country, unloading_point_zip, unloading_point_city,
            pallet_type, quantity, loading_meters, volume, weight,
            loading_date, delivery_date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, orders_demo)

    # Katteet 8–20 % jokaisella keikalla. Polttoainelisä 200 = 19 % rahdista
    # (toukokuun demokerroin 1.19). Trailervuokra 400: kulu- ja myyntirivi
    # (päivät × leasing_rate / rental_rate, kuten vahvistusautomaatti).
    # Suunnitelluilla keikoilla ei vielä 400-rivejä (lisätään vahvistuksessa).
    # Spot-keikalla (TRP-2026-005) myynti on vain koodi 100: trailervuokra
    # ja muut lisät sisältyvät spot-hintaan, joten 400 on vain kulurivinä.
    costs_demo = [
        # Trip 1 — Suunniteltu FI→DE (2 orderia)
        (trip_db_ids[0], "120", "FREIGHT", "3400.00", "revenue", None),
        (trip_db_ids[0], "200", "POLTTOAINELISÄ", "646.00", "revenue", None),
        (trip_db_ids[0], "210", "KOTIMAAN AJO, KUORMATTU", "180.00", "cost", None),
        (trip_db_ids[0], "500", "LAUTTA", "1050.00", "cost", None),
        (trip_db_ids[0], "220", "MANTEREEN AJO, KUORMATTU", "1950.00", "cost", None),
        (trip_db_ids[0], "300", "SAKSAN TIEMAKSU", "120.00", "cost", None),
        # Trip 2 — Vahvistettu FI→SE lautta
        (trip_db_ids[1], "120", "FREIGHT", "1450.00", "revenue", None),
        (trip_db_ids[1], "200", "POLTTOAINELISÄ", "275.50", "revenue", None),
        (trip_db_ids[1], "400", "TRAILERVUOKRA (myynti) 2 pv x 70 €", "140.00", "revenue", None),
        (trip_db_ids[1], "400", "TRAILERVUOKRA (osto) 2 pv x 45 €", "90.00", "cost", None),
        (trip_db_ids[1], "210", "KOTIMAAN AJO, KUORMATTU", "120.00", "cost", None),
        (trip_db_ids[1], "500", "LAUTTA", "680.00", "cost", None),
        (trip_db_ids[1], "220", "MANTEREEN AJO, KUORMATTU", "650.00", "cost", None),
        # Trip 3 — Käynnissä FI→NL (3 orderia)
        (trip_db_ids[2], "120", "FREIGHT", "4300.00", "revenue", None),
        (trip_db_ids[2], "200", "POLTTOAINELISÄ", "817.00", "revenue", None),
        (trip_db_ids[2], "400", "TRAILERVUOKRA (myynti) 5 pv x 54 €", "270.00", "revenue", None),
        (trip_db_ids[2], "400", "TRAILERVUOKRA (osto) 5 pv x 35 €", "175.00", "cost", None),
        (trip_db_ids[2], "210", "KOTIMAAN AJO, KUORMATTU", "160.00", "cost", None),
        (trip_db_ids[2], "500", "LAUTTA", "1050.00", "cost", None),
        (trip_db_ids[2], "220", "MANTEREEN AJO, KUORMATTU", "2800.00", "cost", None),
        (trip_db_ids[2], "310", "HOLLANTI + SAKSA TIEMAKSU", "260.00", "cost", None),
        # Trip 4 — Toimitettu FI→DE (2 orderia)
        (trip_db_ids[3], "120", "FREIGHT", "4100.00", "revenue", None),
        (trip_db_ids[3], "200", "POLTTOAINELISÄ", "779.00", "revenue", None),
        (trip_db_ids[3], "400", "TRAILERVUOKRA (myynti) 4 pv x 67 €", "268.00", "revenue", None),
        (trip_db_ids[3], "400", "TRAILERVUOKRA (osto) 4 pv x 43 €", "172.00", "cost", None),
        (trip_db_ids[3], "210", "KOTIMAAN AJO, KUORMATTU", "720.00", "cost", None),
        (trip_db_ids[3], "500", "LAUTTA", "1050.00", "cost", None),
        (trip_db_ids[3], "220", "MANTEREEN AJO, KUORMATTU", "2350.00", "cost", None),
        (trip_db_ids[3], "300", "SAKSAN TIEMAKSU", "190.00", "cost", None),
        # Trip 5 — Laskutettu FI→EE, spot
        (trip_db_ids[4], "100", "SPOT", "1650.00", "revenue", None),
        (trip_db_ids[4], "400", "TRAILERVUOKRA (osto) 2 pv x 42 €", "84.00", "cost", None),
        (trip_db_ids[4], "210", "KOTIMAAN AJO, KUORMATTU", "150.00", "cost", None),
        (trip_db_ids[4], "500", "LAUTTA", "620.00", "cost", None),
        (trip_db_ids[4], "510", "SATAMAMAKSU", "60.00", "cost", None),
        (trip_db_ids[4], "220", "MANTEREEN AJO, KUORMATTU", "440.00", "cost", None),
        # Trip 6 — Vahvistettu FI→PL (2 orderia)
        (trip_db_ids[5], "120", "FREIGHT", "3600.00", "revenue", None),
        (trip_db_ids[5], "200", "POLTTOAINELISÄ", "684.00", "revenue", None),
        (trip_db_ids[5], "400", "TRAILERVUOKRA (myynti) 5 pv x 59 €", "295.00", "revenue", None),
        (trip_db_ids[5], "400", "TRAILERVUOKRA (osto) 5 pv x 38 €", "190.00", "cost", None),
        (trip_db_ids[5], "210", "KOTIMAAN AJO, KUORMATTU", "330.00", "cost", None),
        (trip_db_ids[5], "500", "LAUTTA", "620.00", "cost", None),
        (trip_db_ids[5], "220", "MANTEREEN AJO, KUORMATTU", "2600.00", "cost", None),
        (trip_db_ids[5], "350", "PUOLAN TIEMAKSU", "140.00", "cost", None),
        # Trip 7 — Suunniteltu FI→NO
        (trip_db_ids[6], "120", "FREIGHT", "2600.00", "revenue", None),
        (trip_db_ids[6], "200", "POLTTOAINELISÄ", "494.00", "revenue", None),
        (trip_db_ids[6], "210", "KOTIMAAN AJO, KUORMATTU", "160.00", "cost", None),
        (trip_db_ids[6], "500", "LAUTTA", "690.00", "cost", None),
        (trip_db_ids[6], "220", "MANTEREEN AJO, KUORMATTU", "1900.00", "cost", None),
    ]
    # Summat euroina (merkkijonoina, ei floatina) → sentit
    cursor.executemany(
        "INSERT INTO costs (trip_id, cost_code, description, amount_cents, cost_type, custom_description) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [(trip, code, desc, money.to_cents(amount), ctype, custom)
         for trip, code, desc, amount, ctype, custom in costs_demo],
    )


def reset_db(db_path):
    """Puhdas demokanta (sama kuin python reset_demo.py)."""
    from reset_demo import reset_demo
    reset_demo(db_path)
    print("Tietokanta alustettu onnistuneesti.")


if __name__ == "__main__":
    from db_config import get_db_path
    reset_db(get_db_path())

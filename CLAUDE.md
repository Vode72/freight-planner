# Freight Planner — CLAUDE.md

TMS-tyylinen kuljetustenhallintatyökalu portfolioprojektina.
React 19 (Create React App / react-scripts 5) + Python Flask + SQLite. Kaikki data on keksittyä demodataa.

---

## Käynnistys

**Tuetut Python-versiot: 3.11 ja 3.15.** CI ajaa backendin testit molemmilla
(`.github/workflows/tests.yml`, matriisi `["3.11", "3.15"]`, `allow-prereleases: true`).

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python reset_demo.py          # puhdas demokanta: skeema + migraatiot + demodata
python app.py                 # http://127.0.0.1:5000

# Frontend
cd frontend
npm install
npm start                     # http://localhost:3000
```

Kirjautuminen: `demo` / `freight2024`

---

## Tietokanta

- Polku: ympäristömuuttuja `FREIGHT_DB_PATH`, oletus `backend/freight.db` (`db_config.get_db_path()`).
- `freight.db` **ei ole versionhallinnassa** — luo se komennolla `python reset_demo.py [polku]`.
  Skripti poistaa kantatiedoston, ajaa `alembic upgrade head` ja lisää demodatan
  (`init_db.seed_demo_data()`: 7 trippiä, 12 orderia, 50 kustannusriviä, katteet 8–20 %,
  maarajoitukset, terminaalit, km-/lauttahinnat, lisähinnat, asiakashinnasto).
- Testit eivät koske `backend/freight.db`:hen: `conftest.py` ohjaa `FREIGHT_DB_PATH`:n
  tmp-hakemistoon ja session-vartija tarkistaa, ettei tiedosto muutu.

### Migraatiot (Alembic)

Skeeman **ainoa lähde** ovat revisiot `backend/migrations/versions/` (`render_as_batch=True`).

```bash
cd backend
alembic upgrade head                    # FREIGHT_DB_PATH / backend/freight.db
alembic -x db=polku.db upgrade head     # kohde annettuna
alembic current
alembic revision -m "kuvaus"            # uusi skeemamuutos
```

| Revisio | Sisältö |
|---|---|
| `0001_baseline` | Skeema sellaisenaan kuin se oli ennen Alembicia. Ei muuta dataa; olemassa olevaan kantaan lisää vain puuttuvat taulut/sarakkeet |
| `0002_reference_data` | Palvelukoodisto + 401→400, 831→830, oletusasetukset, fuel_rates → surcharge_rates (vanhat kannat) |
| `0003_money_integer` | REAL-rahasarakkeet → INTEGER (`*_cents`, `*_e4`), muunnos Decimalina, downgrade mukana |
| `0004_tractors` | Vetäjärekisteri `tractors` (trucks-rivit siirretään, taulu pudotetaan), ominaisuussarakkeet trailereille, `trips.tractor_id`, downgrade mukana |
| `0005_trailer_identity` | Trailerin rekisteri valinnainen + uniikki kun ei NULL, tunniste pakollinen + uniikki, status-CHECK (+ Poistettu), `trailer_maintenance.trailer_id` → INTEGER FK `trailers.id`. Pysähtyy tuplista, orvoista huolloista (tulostaa siivous-SQL:n) ja tuntemattomasta statuksesta; downgrade pysähtyy rekisterittömiin trailereihin |

- Koko upgrade on yksi transaktio: virhe ei jätä kantaa puolitiehen.
- **Varmuuskopio ennen migraatiota:** `upgrade_db()` (myös `app.migrate_db()`) ja `alembic`-CLI
  kopioivat olemassa olevan kannan, jonka revisio ei ole head, ensin tiedostoon
  `<kanta>.bak-<revisio>-<aikaleima>` (`db_migrate.backup_if_pending`, SQLiten backup-API).
  Uutta/tyhjää kantaa ei kopioida. Kopiot ovat `.gitignore`ssa.
- Koodista: `db_migrate.upgrade_db(polku)` tai `upgrade_connection(conn)` (myös muistikanta).
  `init_db.create_schema(conn)` = upgrade head. Jokaisen upgraden jälkeen palvelukoodisto
  synkronoidaan `services.SERVICES`-listasta.
- `app.py` ajaa käynnistyessään (`python app.py`, ei importissa) `migrate_db()` = upgrade head.
- `migrate_*.py` ovat ohuita yhteensopivuuskääreitä (`upgrade head`), eivät lisää demodataa.
- **Demodata ei kuulu migraatioihin.** Valmiita revisioita ei muokata — muutos = uusi revisio.
- **FK-sarakkeisiin tyyppitarkistus (käytäntö):** uusi tai uudelleen luotava viiteavainsarake saa
  `CHECK (typeof(sarake) = 'integer')` (nullable: `sarake IS NULL OR typeof(sarake) = 'integer'`).
  SQLite tallentaa muuten hiljaa tekstiä INTEGER-sarakkeeseen (esim. rekisterinumeron id:n paikalle),
  eikä viiteavaimia valvota (`PRAGMA foreign_keys` ei ole päällä). Mukana: `trailer_maintenance.trailer_id`.
  Puuttuu vielä: `trips.trailer_id/carrier_id/tractor_id/unloading_terminal_id`, `orders.trip_id`,
  `costs.trip_id`, `customer_rate_cards.customer_id`, `customer_billing_rules.customer_id`,
  `tractors.carrier_id` (lisätään uudella revisiolla, kun taulu luodaan seuraavan kerran uudelleen).

### Rahamuoto

**Kanta: INTEGER kiinteällä mittakaavalla. Laskenta: `Decimal`. API: euroina numeroina.**
`backend/money.py` on ainoa paikka, jossa raha muunnetaan muodosta toiseen.

| Mittakaava | Pääte | Käyttö | Esimerkki |
|---|---|---|---|
| ×100 (sentit) | `*_cents` | summat, kiinteät hinnat, €/pv | 180,00 € → `18000` |
| ×10 000 | `*_e4` | yksikköhinnat (€/km, €/100 kg) ja prosentit | 12,345 % → `123450`, 1,85 €/km → `18500` |

Sarakkeet: `costs.amount_cents`, `trailers.leasing_rate_cents/rental_rate_cents`, `ferry_rates.price_cents`,
`km_rates.domestic_rate_e4/continent_rate_e4`, `surcharge_rates.rate_e4/min_amount_cents/max_amount_cents`,
`customer_rate_cards.freight_price_cents`, `customer_billing_rules.rate_e4`.

Miksi kokonaisluvut eikä Decimal kannassa:
- SQLitessä ei ole desimaalityyppiä: `DECIMAL`/`NUMERIC` tallentuu REALina → sama float-ongelma.
- Decimal tekstinä rikkoisi `SUM()`-, vertailu- ja `CHECK`-lausekkeet. Kokonaisluvuilla
  `SUM()` on tarkka suoraan SQL:ssä (dashboardit summaavat kannassa).
- Sarakkeen pääte kertoo mittakaavan, ja uudelleennimeäminen kaataa unohtuneen kyselyn heti
  eikä palauta hiljaa satakertaista summaa. `CHECK (typeof(x) = 'integer')` estää floatit.

Säännöt:
- Ei `float()`:ia eikä `round()`:ia rahalaskennassa — `money.round_money()` (ROUND_HALF_UP),
  `money.total()`, `money.percent_of()`. Testi `test_no_float_in_money_code` valvoo tätä.
- Rivit kannasta: `money.row_from_db(taulu, rivi)` → API-kentät Decimalina; kantaan:
  `money.values_to_db(taulu, data)`. Syöte: `money.parse_field()` (numero tai "12,50"; virhe → 400).
- `app.MoneyJSONProvider` muuntaa Decimalin JSON-numeroksi (vain serialisointi).
- Frontend lähettää rahasyötteet merkkijonoina (ei `parseFloat`).

---

## Testit

```bash
cd backend
pytest tests/ -v
```

Frontend:

```bash
cd frontend
npm test
```

---

## Kansiorakenne

```
freight-planner/
├── backend/
│   ├── app.py                    # Kaikki REST API -endpointit (~2100 riviä)
│   ├── restriction_engine.py     # Ajokieltologiikka (maarajoitukset)
│   ├── services.py               # Palvelukoodisto (SERVICES) + migraatiofunktiot
│   ├── surcharges.py             # Lisähinnat: calculate_surcharge, derive_trade_type, demodata
│   ├── customer_pricing.py       # Asiakashinnasto + lisäsäännöt: find_rate_card, get_billing_rule
│   ├── money.py                  # Rahamuunnokset: Decimal ↔ *_cents / *_e4 ↔ API
│   ├── equipment.py              # Kalusto: ominaisuudet (FEATURES), vetäjien koodistot ja validointi
│   ├── db_config.py              # get_db_path(): FREIGHT_DB_PATH / backend/freight.db
│   ├── db_migrate.py             # Alembic koodista: upgrade_db / upgrade_connection
│   ├── alembic.ini
│   ├── migrations/               # Alembic: env.py + versions/0001–0005
│   ├── reset_demo.py             # Puhdas demokanta yhdellä komennolla
│   ├── init_db.py                # create_schema() (= upgrade head) + seed_demo_data() + reset_db()
│   ├── migrate_*.py              # Yhteensopivuuskääreet: alembic upgrade head
│   ├── requirements.txt
│   ├── pytest.ini
│   └── tests/
│       ├── conftest.py           # Testifixturet (tmp_path-kanta, Alembic + demodata)
│       ├── test_alembic.py       # Migraatiot: tyhjä/vanha kanta, rahamuunnos, trucks→tractors, trailerien yksikäsitteisyys, downgrade, rollback, CLI, varmuuskopio
│       ├── test_tractors.py      # Vetäjät: CRUD, carrier-validointi, pikaluonti, ominaisuudet (myös trailerit)
│       ├── test_trailers.py      # Trailerit: rekisteri/tunniste 409, vaihtokori, Poistettu, DELETE 409, huoltohistoria id:llä
│       ├── test_money.py         # Rahapyöristys (0,1 + 0,2), Decimal ↔ sentit, API-muoto
│       ├── test_id_gen.py        # ID-generoinnin testit
│       ├── test_services.py      # Palvelukoodiston ja migraation testit
│       ├── test_surcharges.py    # Lisähintojen laskenta, hakujärjestys, voimassaolo, CRUD
│       ├── test_fuel_migration.py # Polttoainelisän siirto, summien vastaavuus, /api/fuel-rates
│       ├── test_customer_pricing.py # Asiakashinnasto (zip/maa-haku, voimassaolo), lisäsäännöt, CRUD
│       ├── test_costs.py        # Kustannuslogiikan testit
│       ├── test_demo_data.py    # Demonimet ("Demo"), katteet 8–20 %, spot, 400-rivit
│       ├── test_db_path.py      # FREIGHT_DB_PATH, ei migraatiota importissa, reset_demo
│       └── test_dashboard.py    # /api/dashboard-summat = costs-taulu (ei kertaudu orderien määrällä)
└── frontend/
    └── src/
        ├── App.js                # Sidebar-layout, reititys
        └── components/
            ├── Dashboard.js
            ├── TripList.js / TripDetail.js / TripForm.js
            ├── OrderList.js / OrderForm.js / AddToTripModal.js
            ├── CustomerList.js / CustomerForm.js
            ├── CostCalculator.js / CostsDashboard.js
            ├── DriverPage.js
            ├── CountryRestrictionsPage.jsx
            ├── HallintaKalusto.jsx / HallintaHinnoittelu.jsx / HallintaAsetukset.jsx
            └── FuelRateManager.js
```

---

## Koodikäytännöt

- **Inline CSS kaikkialla** — ei erillistä CSS-tiedostoa
- **JavaScript** (ei TypeScript)
- **Suomenkielinen UI**, englanti koodissa
- **Tumma teema**: `#0f172a` tausta, `#f97316` oranssi aksentti
- **API base URL**: `http://127.0.0.1:5000/api/`
- **React Router v7** nested routes — URL-parametri `:tab` välilehtiin
- Ei viittauksia oikeisiin työnantajiin tai yrityksiin — kaikki data on demodataa
- Kulukoodit ovat aina keksittyjä demokoodeja

---

## Bisneslogiikka — automaatit

| Tapahtuma | Automaatti |
|---|---|
| Koodi 120 (FREIGHT) lisätään | Koodi 200 (POLTTOAINELISÄ) lisätään automaattisesti `calculate_surcharge("200", …)` -funktiolla (surcharge_rates, percent) |
| Trip vahvistetaan (→ Vahvistettu) | Kaksi koodin 400 riviä (TRAILERVUOKRA, cost + revenue) lisätään päivien mukaan |
| FEC loading_started >30 min myöhässä | Koodi 800 (ODOTUSAIKA) lisätään automaattisesti |
| FEC delivery_completed kuitataan | `delivered_at`-timestamp asetetaan (OTD-laskenta) |
| Laskutettu-status | Trip lukitaan — ei muutoksia mahdollisia |

**Palvelukoodisto** on `services`-taulussa (`GET /api/services`; `/api/cost-codes` käyttää samaa dataa).
Koodi = palvelu, `cost_type` = suunta: sama koodi voi olla sekä osto- että myyntirivillä
(esim. 400 trailervuokra, 830 ylikäyttö). Vanhat koodit 401 ja 831 on yhdistetty niihin.

**Lisähinnat** ovat `surcharge_rates`-taulussa (`/api/surcharge-rates`, CRUD), spec luku 7.
`calculate_surcharge(service_code, context, conn)` valitsee voimassa olevan, tarkimman rivin
(painot: maa 8 > tuote 4 > operaattori 2 > suunta 1; tyhjä kenttä = kaikki) ja laskee
summan (`percent` rahdista, `fixed`, `per_100kg`, `per_km`) + min/max, pyöristys ROUND_HALF_UP.
`cost_type` on pakollinen sekä rivillä että contextissa (myynti ≠ osto, esim. ETS 150 € / 180 €).
Ei hintaa → `None`; puuttuva lähtötieto → `ValueError`. Sama kohdistus + päällekkäinen
voimassaolo → API palauttaa 409. `derive_trade_type(lastausmaa, purkumaa)` → DOM/EXP/IMP/CROSS.

**Asiakashinnoittelu** (spec luku 8): `customer_rate_cards` (`/api/customers/:id/rate-cards`, `/api/rate-cards/:id`)
ja `customer_billing_rules` (`/api/customers/:id/billing-rules`, `/api/billing-rules/:id`), CRUD + 409 päällekkäisyydestä.
`find_rate_card(conn, customer_id, origin, dest, product_type, date)` — origin/dest `{country, zip}` tai maakoodi;
postinumeroalueosuma (postinumeron alku) ennen pelkkää maata, pidempi alue voittaa. Ei osumaa → `None`.
`get_billing_rule(conn, customer_id, service_code, date)` → `{billed, rate_type, rate, …}` tai `None` (= listahinta).
`rate_type` tyhjä = listahinta, `pass_through` sallittu vain säännöissä (`rate` = kate-%, tyhjä = 0 %).
Asiakkaan poisto poistaa myös hinnaston ja säännöt.

**Polttoainelisä** (spec 7.5) on `surcharge_rates`-taulussa: 200 / revenue / percent, kohdistus tyhjä.
`migrate_fuel_rates()` siirsi `fuel_rates`-rivit kertaluonteisesti (`rate = (m − 1) × 100`, Decimal, 4 desimaalia,
kerroin ≤ 1 ohitetaan, merkintä `schema_migrations`-tauluun). `fuel_rates`-taulua ei enää käytetä
koodissa (poisto UI-vaiheessa). `/api/fuel-rates` on yhteensopivuuskerros FuelRateManagerille:
sama vastausmuoto, `multiplier = 1 + rate / 100`.

**Oletus-cost_type (`default_cost_type`):**
- `revenue`: 100, 120, 200, 230, 720
- `cost`: kaikki muut

**Statusketju**: Suunniteltu → Vahvistettu → Käynnissä → Toimitettu → Laskutettu

---

## Kalusto: vetäjät ja trailerit

**Vetäjärekisteri** on `tractors`-taulussa (`/api/tractors`, CRUD; korvasi `trucks`-taulun ja `/api/trucks`:n).
Koodistot ja validointi ovat `backend/equipment.py`:ssä (`GET /api/equipment-meta`).
- `registration_number` uniikki: tallennetaan trimmattuna isoin kirjaimin, `UNIQUE COLLATE NOCASE`;
  varattu rekisteri → 409 + `existing`-rivi (UI voi tarjota olemassa olevaa).
- `vehicle_type` vetoauto / kuorma-auto; `max_weight` (kg), `max_ldm`, `max_volume` (m³) vain
  kuorma-autolle (API 400 + `CHECK`). `status` aktiivinen / huollossa / poistettu (poistetut piilossa listasta).
- POST palauttaa koko rivin (`{id, tractor}`): pikaluonti = `registration_number` + `carrier_id` + `vehicle_type`.
  PUT on osittainen. Käytetyn vetäjän DELETE → 409 (aseta status poistettu); kuljetusyhtiön DELETE → 409,
  jos sillä on vetäjiä (ei ketjupoistoa).

**Ominaisuudet** (`adr`, `temperature_controlled`, `tail_lift`, `crane`) ovat samannimisiä 0/1-sarakkeita
sekä `tractors`- että `trailers`-taulussa (samat nimet kuin trips/orders-lipuilla). API:ssa molemmilla
`features: {"adr": false, …}`. Uusi ominaisuus = uusi Alembic-revisio + `equipment.FEATURES`.
Trailereilla ei ole carrieria (leasing-pooli).

**Trailerit** (`/api/trailers`, Alembic 0005):
- `plate_number` valinnainen (vaihtokoreilla ei rekisteriä), normalisoitu kuten vetäjillä, uniikki kun ei NULL;
  `identifier` pakollinen ja uniikki (kirjainkoosta riippumatta), tyhjä tunniste = rekisterinumero.
- Pikaluonti: `trailer_type` + `plate_number` tai `identifier` (lämpösäätö tyypin mukaan). Varattu rekisteri
  tai tunniste → 409 + `field` + `existing` (POST ja PUT). PUT on osittainen.
- `status` Vapaa / Käytössä / Huollossa / Poistettu. Poistetut piilossa (`?include_removed=1` näyttää);
  Poistettua traileria ei voi valita uudelle keikalle (jo valittu saa jäädä).
- DELETE → 409, jos trailerilla on keikkoja (myös laskutettuja) tai huoltohistoriaa: aseta status Poistettu.
- Huoltohistoria (`trailer_maintenance.trailer_id`) viittaa trailerin id:hen: rekisterin muutos ei irrota sitä,
  eikä samalla rekisterillä luotu uusi traileri peri vanhaa historiaa.

**PUT `/api/tractors/:id` ja `/api/trailers/:id` ovat osittaisia:** puuttuva kenttä säilyttää arvonsa,
`null` tyhjentää sen. Tyhjennys noudattaa kentän sääntöjä:
- valinnainen kenttä → NULL (vetäjä: `make_model`, `emission_class`, kapasiteetti, `notes`;
  traileri: `plate_number` → rekisteritön/vaihtokori, `leasing_company`)
- pakollinen kenttä → 400 (vetäjä: `registration_number`, `carrier_id`, `vehicle_type`; traileri: `trailer_type`,
  sekä `identifier`, jos rekisteriäkään ei ole)
- oletusarvollinen kenttä → oletus (`status` → aktiivinen / Vapaa; trailerin `identifier` → rekisterinumero;
  `leasing_rate`/`rental_rate` → 0)
- `features`: puuttuva avain säilyy, `{"adr": null}` = false, `"features": null` = kaikki false

**Tripin vetäjä** (`trips.tractor_id`, nullable): `tractor.carrier_id = trip.carrier_id`, muuten 400.
Tripillä ei carrieria → carrier asetetaan vetäjältä. Poistettua vetäjää ei voi valita (jo valittu saa jäädä).
PUT ilman `tractor_id`-avainta säilyttää vetäjän, `null` poistaa sen. Vetäjän carrierin vaihto → 409,
jos se on laskuttamattomalla tripillä. Traileri on tripillä valinnainen.

**`trips.truck_plate` on palvelimen täyttämä snapshot**, ei asiakkaan syöte. Peruste: laskutetun
keikan dokumentit (Transport Order, CMR, lasku) on annettu sillä rekisterinumerolla, joka keikalla oli —
jos vetäjän rekisteri myöhemmin korjataan tai vetäjä siirtyy toiselle carrierille, laskutetun keikan
dokumenttitieto ei saa muuttua. Laskuttamattomilla keikoilla kopio seuraa vetäjää, jotta tulevat
dokumentit tulostuvat korjatulla rekisterillä. Siksi: vetäjä valitaan → kopio rekisteristä; sama vetäjä →
kopio säilyy; vetäjä vaihtuu → uusi kopio; vetäjä poistetaan keikalta → NULL; vetäjän rekisteriä
muokataan (`PUT /api/tractors/:id`) → kopio päivitetään kaikille sen laskuttamattomille keikoille
(vastauksessa `updated_trips`), laskutetut pysyvät jäädytettyinä. Nykyinen rekisteri tulee kyselyissä
kentässä `tractor_registration`. Vanhat keikat, joita 0004 ei voinut linkittää (rekisteri/carrier ei
täsmännyt), säilyttävät tekstinsä.

---

## Työskentelysäännöt

- **Session alussa tarkista CI-tila** avoimen haaran/PR:n viimeisimmästä commitista (GitHub Actions).
  Jos CI epäonnistuu: raportoi syy ja korjausehdotus — **älä pushaa korjausta ilman hyväksyntää**.
  PR:iä ei seurata jatkuvasti.
- Tee **aina ensin suunnitelma** ja odota hyväksyntää ennen koodausta
- Työskentele **omassa haarassa** — yhdistä main-haaraan vasta kun testit menevät läpi
- **Ei viittauksia oikeisiin työnantajiin tai yrityksiin** — käytä aina demodataa
- **Kulukoodit ovat aina keksittyjä demokoodeja**
- **Päivitä `FREIGHT_PLANNER_KONTEKSTI.txt`** session lopuksi kun merkittäviä muutoksia tehty

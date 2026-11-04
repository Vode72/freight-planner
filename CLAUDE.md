# Freight Planner — CLAUDE.md

TMS-tyylinen kuljetustenhallintatyökalu portfolioprojektina.
React 18 + Python Flask + SQLite. Kaikki data on keksittyä demodataa.

---

## Käynnistys

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python init_db.py
python migrate_restrictions.py
python migrate_hallinta.py
python migrate_settings.py
python migrate_services.py
python migrate_surcharges.py
python migrate_customer_pricing.py
python app.py                 # http://127.0.0.1:5000

# Frontend
cd frontend
npm install
npm start                     # http://localhost:3000
```

Kirjautuminen: `demo` / `freight2024`

---

## Tietokannan ensiasennus

Aja järjestyksessä `backend/`-hakemistossa:

| Skripti | Luo |
|---|---|
| `python init_db.py` | Perustaulut + demodataa (7 trippiä, 12 orderia, 15 kustannusriviä) |
| `python migrate_restrictions.py` | country_restrictions, terminals, trips.tail_lift_unloading |
| `python migrate_hallinta.py` | trailer_maintenance, km_rates, ferry_rates, trailerin huoltosarakkeet |
| `python migrate_settings.py` | settings (yritystiedot + hälytyskonfiguraatio) |
| `python migrate_services.py` | services (palvelukoodisto) + vanhojen koodien yhdistäminen 401→400, 831→830 |
| `python migrate_surcharges.py` | surcharge_rates (lisähinnat) + demodata tyhjään tauluun + fuel_rates → surcharge_rates (200) |
| `python migrate_customer_pricing.py` | customer_rate_cards + customer_billing_rules + demodata (Nordic Demo Plastics Oy, Baltic Demo Trading Oy) |

`app.py` ajaa käynnistyessään `migrate_db()` joka lisää FEC-timestampit automaattisesti
jos niitä ei vielä ole, sekä palvelukoodiston (`services.py`), lisähintojen (`surcharges.py`) ja asiakashinnoittelun (`customer_pricing.py`) migraation
(idempotent, turvallinen uudelleenajoon).

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
│   ├── init_db.py                # create_schema() + seed_demo_data() + reset_db()
│   ├── migrate_restrictions.py   # country_restrictions, terminals
│   ├── migrate_hallinta.py       # trailer_maintenance, km_rates, ferry_rates
│   ├── migrate_settings.py       # settings-taulu
│   ├── migrate_services.py       # services-taulu + 401→400, 831→830
│   ├── migrate_surcharges.py     # surcharge_rates-taulu + demodata
│   ├── migrate_customer_pricing.py # customer_rate_cards, customer_billing_rules + demodata
│   ├── requirements.txt
│   ├── pytest.ini
│   └── tests/
│       ├── conftest.py           # Testifixturet (tmp_path-kanta)
│       ├── test_id_gen.py        # ID-generoinnin testit
│       ├── test_services.py      # Palvelukoodiston ja migraation testit
│       ├── test_surcharges.py    # Lisähintojen laskenta, hakujärjestys, voimassaolo, CRUD
│       ├── test_fuel_migration.py # Polttoainelisän siirto, summien vastaavuus, /api/fuel-rates
│       ├── test_customer_pricing.py # Asiakashinnasto (zip/maa-haku, voimassaolo), lisäsäännöt, CRUD
│       └── test_costs.py        # Kustannuslogiikan testit
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
`migrate_fuel_rates()` siirsi `fuel_rates`-rivit kertaluonteisesti (`rate = round((m − 1) × 100, 4)`,
kerroin ≤ 1 ohitetaan, merkintä `schema_migrations`-tauluun). `fuel_rates`-taulua ei enää käytetä
koodissa (poisto UI-vaiheessa). `/api/fuel-rates` on yhteensopivuuskerros FuelRateManagerille:
sama vastausmuoto, `multiplier = 1 + rate / 100`.

**Oletus-cost_type (`default_cost_type`):**
- `revenue`: 100, 120, 200, 230, 720
- `cost`: kaikki muut

**Statusketju**: Suunniteltu → Vahvistettu → Käynnissä → Toimitettu → Laskutettu

---

## Työskentelysäännöt

- Tee **aina ensin suunnitelma** ja odota hyväksyntää ennen koodausta
- Työskentele **omassa haarassa** — yhdistä main-haaraan vasta kun testit menevät läpi
- **Ei viittauksia oikeisiin työnantajiin tai yrityksiin** — käytä aina demodataa
- **Kulukoodit ovat aina keksittyjä demokoodeja**
- **Päivitä `FREIGHT_PLANNER_KONTEKSTI.txt`** session lopuksi kun merkittäviä muutoksia tehty

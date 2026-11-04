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

`app.py` ajaa käynnistyessään `migrate_db()` joka lisää FEC-timestampit automaattisesti
jos niitä ei vielä ole, sekä palvelukoodiston migraation (`services.py`)
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
│   ├── init_db.py                # create_schema() + seed_demo_data() + reset_db()
│   ├── migrate_restrictions.py   # country_restrictions, terminals
│   ├── migrate_hallinta.py       # trailer_maintenance, km_rates, ferry_rates
│   ├── migrate_settings.py       # settings-taulu
│   ├── migrate_services.py       # services-taulu + 401→400, 831→830
│   ├── requirements.txt
│   ├── pytest.ini
│   └── tests/
│       ├── conftest.py           # Testifixturet (tmp_path-kanta)
│       ├── test_id_gen.py        # ID-generoinnin testit
│       ├── test_services.py      # Palvelukoodiston ja migraation testit
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
| Koodi 120 (FREIGHT) lisätään | Koodi 200 (POLTTOAINELISÄ) lisätään automaattisesti `fuel_rates`-kertoimella |
| Trip vahvistetaan (→ Vahvistettu) | Kaksi koodin 400 riviä (TRAILERVUOKRA, cost + revenue) lisätään päivien mukaan |
| FEC loading_started >30 min myöhässä | Koodi 800 (ODOTUSAIKA) lisätään automaattisesti |
| FEC delivery_completed kuitataan | `delivered_at`-timestamp asetetaan (OTD-laskenta) |
| Laskutettu-status | Trip lukitaan — ei muutoksia mahdollisia |

**Palvelukoodisto** on `services`-taulussa (`GET /api/services`; `/api/cost-codes` käyttää samaa dataa).
Koodi = palvelu, `cost_type` = suunta: sama koodi voi olla sekä osto- että myyntirivillä
(esim. 400 trailervuokra, 830 ylikäyttö). Vanhat koodit 401 ja 831 on yhdistetty niihin.

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

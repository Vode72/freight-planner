# Hinnoittelumoottori — määrittely

**Projekti:** Freight Planner (TMS)
**Versio:** 1.0 (11/2026)
**Tila:** Hyväksytty toteutettavaksi

> Kaikki tämän dokumentin koodit, hinnat, prosentit ja asiakkaat ovat keksittyä demodataa.

---

## 1. Tausta ja tavoite

Nykyisessä Freight Plannerissa kulut ja myynnit kirjataan tripille pääosin käsin. Automaatiota on kolmessa kohdassa: polttoainelisä (koodi 120 → 200), trailervuokra vahvistuksessa (400) ja odotusaika FEC-kuittauksesta (800). Lautta- ja km-hinnat ovat tietokannassa, mutta niitä ei käytetä automaattisesti.

Todellisessa liikenteenhoidossa tilauksen avaus etenee näin: asiakkaalla on sovittu hinnasto, rahtirivi haetaan siitä ja lisät lasketaan päälle sovittujen sääntöjen mukaan. Ajoittain annetaan kertahinta (spot), joka sisältää kaiken. Lisien hinnat muuttuvat säännöllisesti (esim. polttoainelisä kuukausittain), joten hinnoittelun pitää muistaa, mikä hinta oli voimassa milloinkin.

**Tavoite:**
1. Tilauksen hinta muodostuu automaattisesti asiakkaan hinnastosta ja lisäsäännöistä. Dispatcher tarkistaa ja hyväksyy rivit.
2. Tripin kulut syntyvät automaattisesti km-, lautta- ja kalustotiedoista.
3. Kate voidaan raportoida tilaus-, trip-, asiakas- ja reittitasolla, mukaan lukien se, kattavatko asiakkaalta peritty lisät todelliset kulut.

---

## 2. Rajaus

**Mukana**
- Palvelukoodisto tietokantaan ja koodiston yhtenäistäminen
- Yleiset lisähinnat voimassaoloineen
- Asiakaskohtaiset hinnastot ja lisäsäännöt
- Sopimus- ja spot-hinnoittelu
- Automaattiset kulurivit (km, lautta, lauttalisät)
- Tripin kulujen kohdistus tilauksille
- Katteen ja lisien kattavuuden raportointi

**Ei mukana (myöhemmin)**
- Laskun PDF-generointi ja Credit Note (oma kokonaisuutensa)
- Tarjouslaskenta asiakkaalle ennen tilausta (CostCalculator säilyy erillisenä)
- Maakohtaisen km-jakauman automaattinen laskenta reitiltä
- Valuutat (kaikki euroina)

---

## 3. Käsitteet

| Termi | Merkitys |
|---|---|
| Palvelukoodi | Numero, joka yksilöi palvelun tai lisän (esim. 120 rahti, 530 ETS-lisä) |
| cost_type | Rivin suunta: `cost` = osto, `revenue` = myynti |
| line_type | `invoice` = laskutetaan / kirjataan, `info` = erittely, ei vaikuta katteeseen |
| Sopimushinta | Asiakkaan hinnastosta haettu rahti (120) + lisät |
| Spot-hinta | Kertahinta (100), joka sisältää kaiken |
| Lisä (surcharge) | Rahdin päälle laskettava erä: polttoaine, liikkuvuuspaketti, ETS jne. |
| Listahinta | Yleinen lisähinta, joka koskee kaikkia asiakkaita |
| Sopimuslisä | Asiakaskohtainen poikkeus listahinnasta |
| trade_type | Liikennesuunta: EXP, IMP, CROSS, DOM |
| product_type | Kuljetustyyppi: FTL (täyskuorma), LTL (osakuorma/kappaletavara) |
| Maksullinen paino | Laskutuspaino (chargeable weight), voi poiketa bruttopainosta |
| Kattavuus | Asiakkaalta peritty lisä suhteessa saman palvelun todelliseen kuluun |

---

## 4. Periaatteet

1. **Koodi = palvelu, cost_type = suunta.** Sama koodi esiintyy sekä osto- että myyntirivillä. Vanhat koodiparit yhtenäistetään (401 → 400, 831 → 830).
2. **Voimassaolo kaikessa.** Jokaisella hinnalla on `valid_from` ja `valid_to`. Riville tallennetaan tilauksen päivämäärän mukainen hinta, joten hinnan muuttuminen ei muuta vanhoja tilauksia.
3. **Tarkin sääntö voittaa.** Asiakassopimus ohittaa listahinnan. Maakohtainen hinta ohittaa aluehinnan.
4. **Ihminen hyväksyy.** Järjestelmä ehdottaa rivit, ja dispatcher voi muokata, poistaa tai lisätä ennen tallennusta.
5. **Ei kertautuvia lisiä.** Prosenttilisät lasketaan aina pelkästä rahtirivistä, ei toisten lisien päälle.
6. **Trippi kantaa kulut, tilaus kantaa myynnin.** Tripin kulut kohdistetaan tilauksille katelaskentaa varten.
7. **Pyöristys:** kaksi desimaalia, puolikkaat ylöspäin, jokainen rivi erikseen.

---

## 5. Hinnoittelutavat

### 5.1 Sopimushinta (contract)
1. Rahti (120) haetaan asiakkaan hinnastosta reitin ja kuljetustyypin perusteella.
2. Lisät lasketaan asiakkaan lisäsääntöjen mukaan. Jos asiakkaalla ei ole omaa sääntöä lisälle, käytetään listahintaa.
3. Rivit tallennetaan `invoice`-tyyppisinä.

### 5.2 Spot-hinta (spot)
1. Dispatcher syöttää kokonaishinnan (100).
2. Järjestelmä laskee taustalla sopimushinnan mukaiset lisät `info`-riveiksi.
3. Info-rivien avulla nähdään, oliko spot-hinta laskennallista sopimushintaa korkeampi vai matalampi.

**Esimerkki:**

| Koodi | Rivi | line_type | € |
|---|---|---|---|
| 100 | Spot | invoice | 2 600 |
| 120 | Rahti (hinnastosta) | info | 2 000 |
| 200 | Polttoainelisä 25 % | info | 500 |
| 230 | Liikkuvuuspaketti 9 % | info | 180 |
| 530 | ETS-lisä | info | 150 |

Laskutetaan 2 600 €. Laskennallinen sopimushinta olisi ollut 2 830 €, joten spot myytiin 230 € halvemmalla.

Polttoainelisän nykyinen automaatti (120 → 200) toimii jatkossa osana tätä logiikkaa.

---

## 6. Palvelukoodisto

Koodisto siirretään kovakoodatusta listasta `services`-tauluun.

| Ryhmä | Koodi | Nimi | Muutos |
|---|---|---|---|
| Rahti | 100 | SPOT | ennallaan |
| | 120 | FREIGHT | ennallaan |
| | 200 | POLTTOAINELISÄ | korjattu revenue-tyypiksi |
| | 210 | KOTIMAAN AJO, KUORMATTU | tarkennettu |
| | 211 | KOTIMAAN AJO, TYHJÄ | uusi |
| | 212 | KOTIMAAN VETOYKSIKKÖ | uusi |
| | 220 | MANTEREEN AJO, KUORMATTU | tarkennettu |
| | 221 | MANTEREEN AJO, TYHJÄ | uusi |
| | 222 | MANTEREEN VETOYKSIKKÖ | uusi |
| | 230 | LIIKKUVUUSPAKETTILISÄ | uusi |
| Tiemaksut | 300 | SAKSAN TIEMAKSU | ennallaan |
| | 310 | HOLLANTI + SAKSA | ennallaan |
| | 320 | ITÄVALLAN TIEMAKSU | uusi |
| | 330 | RANSKAN TIEMAKSU | uusi |
| | 340 | SVEITSIN TIEMAKSU | uusi |
| | 350 | PUOLAN TIEMAKSU | uusi |
| Kalusto | 400 | TRAILERVUOKRA | 401 yhdistetään tähän |
| | 410 | TANKKAUS | ennallaan |
| | 830 | YLIKÄYTTÖ | 831 yhdistetään tähän |
| Lautta | 500 | LAUTTA | ennallaan |
| | 510 | SATAMAMAKSU | ennallaan |
| | 520 | BUNKKERILISÄ (BAF) | uusi |
| | 530 | PÄÄSTÖKAUPPALISÄ (ETS) | uusi |
| | 540 | MARPOL-LISÄ | uusi |
| Lisät | 600 | ADR | ennallaan |
| | 610 | LÄMPÖTILA | ennallaan |
| | 700 | KÄSITTELY | ennallaan |
| | 720 | HALLINNOINTIMAKSU | uusi |
| | 799–820 | MUUT, ODOTUS, LISÄKÄSITTELY, MUU | ennallaan |

---

## 7. Lisähinnat (listahinnat)

### 7.1 Laskentatavat

| rate_type | Laskenta | Esimerkki |
|---|---|---|
| `percent` | rahti × % | Polttoainelisä 30 % |
| `fixed` | kiinteä € per lähetys | ETS-lisä 150 € |
| `per_100kg` | maksullinen paino / 100 × hinta | MARPOL LTL 0,40 €/100 kg |
| `per_km` | km × hinta | Tiemaksu 0,20 €/km |

Jokaisella rivillä voi olla `min_amount` ja `max_amount`.

### 7.2 Kohdistus

Hinta voi kohdistua seuraavien yhdistelmään (tyhjä = kaikki):
- `trade_type`: EXP / IMP / CROSS / DOM
- `product_type`: FTL / LTL
- `country`: kohdemaa (EXP), lähtömaa (IMP) tai tyhjä (CROSS)
- `operator`: lauttaoperaattori (BAF, ETS)

### 7.3 Hakujärjestys

Tarkin osuma voittaa:
1. Asiakkaan sopimuslisä
2. Listahinta: suunta + tuote + maa
3. Listahinta: suunta + maa
4. Listahinta: suunta
5. Ei hintaa → riviä ei ehdoteta, ja dispatcher saa ilmoituksen

Alueet (esim. Baltia, Keski-Itä-Eurooppa) ovat vain syötön apuväline hallintanäkymässä: yksi aluehinta tallennetaan jokaiselle alueen maalle omaksi rivikseen. Laskenta käyttää aina maata.

### 7.4 Liikennesuunnan päättely

`trade_type` päätellään tilauksen lastaus- ja purkumaasta automaattisesti:

| Lastausmaa | Purkumaa | trade_type |
|---|---|---|
| FI | FI | DOM |
| FI | muu | EXP |
| muu | FI | IMP |
| muu | muu | CROSS |

### 7.5 Polttoainelisän siirto

Nykyinen `fuel_rates.multiplier` siirretään `surcharge_rates`-tauluun prosenttina: `rate = (multiplier − 1) × 100`. FuelRateManager-näkymä korvataan Hinnoittelu → Lisät -välilehdellä.

---

## 8. Asiakashinnoittelu

### 8.1 Hinnasto (`customer_rate_cards`)
Asiakkaan sovitut rahtihinnat reiteittäin:
- lähtömaa ja valinnainen postinumeroalue
- kohdemaa ja valinnainen postinumeroalue
- product_type
- rahtihinta (€)
- voimassaolo

Haku: tarkin postinumeroalueosuma ensin, sitten pelkkä maa.

### 8.2 Lisäsäännöt (`customer_billing_rules`)
Asiakaskohtaisesti jokaiselle lisälle:
- `billed`: laskutetaanko lisä asiakkaalta (kyllä/ei)
- valinnainen oma hinta tai prosentti, muuten listahinta
- voimassaolo

Esimerkki: asiakas A maksaa rahdin, polttoainelisän 25 % (sopimus) ja ETS-lisän listahinnalla. Liikkuvuuspakettia ei laskuteta erikseen.

---

## 9. Hinnanmuodostus tilaukselle

```
Tilaus tallennetaan / dispatcher painaa "Laske hinta"
  │
  ├─ Päättele trade_type (lastaus- ja purkumaa)
  ├─ pricing_type?
  │   ├─ contract → hae rahti (120) asiakkaan hinnastosta
  │   └─ spot     → dispatcher syöttää hinnan (100)
  ├─ Käy läpi kaikki lisät:
  │   ├─ asiakkaan sääntö → billed? oma hinta?
  │   └─ muuten listahinta hakujärjestyksellä
  ├─ contract → lisät invoice-riveiksi
  │  spot     → lisät info-riveiksi
  └─ Näytä ehdotus → dispatcher muokkaa / hyväksyy → tallennus
```

Tilaukselle tarvitaan uudet kentät: `pricing_type` (contract/spot), `product_type` (FTL/LTL), `chargeable_weight`.

---

## 10. Tripin kulut

Vetäjän kulut jaetaan sekä kotimaan että mantereen osuudella kolmeen osaan:

| Osuus | Kuormattu | Tyhjä | Vetoyksikkö |
|---|---|---|---|
| Kotimaa | 210 | 211 | 212 |
| Manner | 220 | 221 | 222 |

- **Kuormattu ajo:** lastauspaikalta purkupaikalle (tai satamaan / satamasta)
- **Tyhjä ajo:** purkupaikalta seuraavalle lastauspaikalle tai lähtöpisteeseen
- **Vetoyksikkö:** kiinteä osa per keikka

Hinnat ovat kuljetusyhtiökohtaisia, koska eri vetäjillä on eri sopimukset. Tyhjät km:t tuottavat samalla Empty % -mittarin (tyhjät km / kaikki km).

| Kulu | Lähde | Milloin |
|---|---|---|
| 210–212 / 220–222 vetäjän kulut | km_rates (carrier) × trip-km:t | km syötetään tripille |
| 500 lautta | ferry_rates reitin mukaan | lauttareitti valitaan |
| 510 satamamaksu | ferry_rates / satama | lauttareitti valitaan |
| 520 BAF, 530 ETS | surcharge_rates operaattorin mukaan | lauttareitti valitaan |
| 300–350 tiemaksut | surcharge_rates (per_km, maa) × toteutuneet km maittain | toteutuneet km syötetään |
| 400 trailervuokra | leasing_rate × päivät | trip vahvistetaan (nykyinen) |
| 800 odotus | FEC-kuittaus | lastaus > 30 min myöhässä (nykyinen) |

**Tiemaksut:** km:t kirjataan maittain (`trip_country_km`), sekä arvioidut että toteutuneet. Asiakkaan tiemaksulisä lasketaan tilauksella arvioiduista km:istä, koska hinta annetaan ennen ajoa. Kulurivi lasketaan toteutuneista km:istä, kun ne syötetään. Erotus näkyy kattavuusraportissa. Kalustoluokka (akselit, päästöluokka) ei vaikuta hintaan ensimmäisessä versiossa.

Automaattirivit näytetään ehdotuksena kuten tilauksella. Jos reitti tai km muuttuu, automaattirivit päivitetään, mutta käsin muokattuja rivejä ei ylikirjoiteta.

TripFormin lauttareitit haetaan jatkossa `ferry_rates`-taulusta, ja kovakoodattu `/api/ferry-routes` poistetaan.

---

## 11. Kate ja kohdistus

- **Tripin kate** = tripin tilausten invoice-myynti − tripin kulut
- **Tilauksen kate** = tilauksen invoice-myynti − tilaukselle kohdistetut kulut
- **Kohdistus:** tripin yhteiset kulut jaetaan tilauksille LDM-osuuden mukaan. LDM on tilauksella pakollinen (vähintään arvio). Paino on varalla vain vanhoille tilauksille, joilta LDM puuttuu. Nykyinen lautan tasajako korvataan tällä.

### 11.1 Rivien sijoittuminen costs-tauluun

Kaikki rivit ovat samassa `costs`-taulussa. `cost_type` kertoo suunnan ja `order_id` kohteen:

| Rivityyppi | cost_type | order_id |
|---|---|---|
| Myynti asiakkaalle | revenue | aina tilaus |
| Keikan yhteinen kulu (ajo, lautta, trailervuokra) | cost | tyhjä |
| Tilauskohtainen kulu (esim. ADR-käsittely, yhden asiakkaan odotus) | cost | tilaus |

**Esimerkki:** trippi, jolla kaksi tilausta

| order_id | koodi | rivi | cost_type | € |
|---|---|---|---|---|
| ORD-021 | 120 | Rahti | revenue | 1 200 |
| ORD-021 | 200 | Polttoainelisä | revenue | 300 |
| ORD-022 | 120 | Rahti | revenue | 800 |
| ORD-022 | 600 | ADR-lisä | revenue | 100 |
| — | 220 | Mantereen ajo, kuormattu | cost | 495 |
| — | 500 | Lautta | cost | 1 010 |
| ORD-022 | 600 | ADR-käsittely | cost | 60 |

- Keikan myynti 2 400 €, kulut 1 565 €, kate 835 €
- ORD-021 (8 LDM) saa 59 % yhteisistä 1 505 €:sta = 885 €
- ORD-022 (5,6 LDM) saa 41 % = 620 € + oma ADR-kulu 60 €

Kohdistettua osuutta ei tallenneta riveiksi. Se lasketaan raportoitaessa, joten se päivittyy automaattisesti, kun tilauksia lisätään keikalle tai poistetaan siltä.

---

## 12. Raportointi

| Näkymä | Kysymys |
|---|---|
| Margin by Order | Kannattaako tämä tilaus? |
| Margin by Trip | Kannattaako tämä keikka kokonaisuutena? |
| Surcharge recovery | Kattaako asiakkaalta peritty ETS/BAF/polttoaine todellisen kulun? Vertailu samalla koodilla myynti vs. kulu. |
| Spot vs. contract | Myytiinkö spot listahintaa kalliimmalla vai halvemmalla? |
| Asiakas- ja reittikate | Kannattavimmat ja heikoimmat asiakkaat ja kohdemaat |

Nämä toimivat myöhemmin Power BI -integraation datalähteenä.

---

## 13. Tietomalli

**Uudet taulut**

```
services
  code (PK), name, category, default_cost_type, active

surcharge_rates
  id, service_code, trade_type, product_type, country, operator,
  rate_type, rate, min_amount, max_amount, valid_from, valid_to

customer_rate_cards
  id, customer_id, origin_country, origin_zip_prefix,
  dest_country, dest_zip_prefix, product_type, freight_price,
  valid_from, valid_to

customer_billing_rules
  id, customer_id, service_code, billed, rate_type, rate,
  valid_from, valid_to

trip_country_km
  id, trip_id, country, estimated_km, realized_km
```

**Muutokset olemassa oleviin**

```
orders:   + pricing_type, product_type, chargeable_weight
costs:    + order_id (nullable), line_type (invoice/info), is_auto
trips:    + domestic_loaded_km, domestic_empty_km,
            continent_loaded_km, continent_empty_km
km_rates: + carrier_id (nullable = oletushinta),
            domestic_loaded_rate, domestic_empty_rate, domestic_unit_fee,
            continent_loaded_rate, continent_empty_rate, continent_unit_fee
```

---

## 14. API

```
GET    /api/services
GET    /api/surcharge-rates            ?service=&country=&date=
POST   /api/surcharge-rates
PUT    /api/surcharge-rates/:id
DELETE /api/surcharge-rates/:id

GET    /api/customers/:id/rate-cards
POST   /api/customers/:id/rate-cards
PUT    /api/rate-cards/:id
DELETE /api/rate-cards/:id

GET    /api/customers/:id/billing-rules
POST   /api/customers/:id/billing-rules
PUT    /api/billing-rules/:id
DELETE /api/billing-rules/:id

POST   /api/orders/:id/price-preview   → ehdotetut rivit, ei tallennusta
POST   /api/orders/:id/price-apply     → tallentaa hyväksytyt rivit
POST   /api/trips/:id/cost-preview
POST   /api/trips/:id/cost-apply

GET    /api/reports/margin             ?level=order|trip|customer|country
GET    /api/reports/surcharge-recovery ?from=&to=
```

---

## 15. Käyttöliittymä

- **Hallinta → Hinnoittelu:** uusi välilehti *Lisät* (surcharge_rates, aluesyöttö, voimassaolon tila). Polttoaine-välilehti yhdistetään tähän.
- **Asiakaskortti:** välilehdet *Perustiedot*, *Hinnasto*, *Lisät*.
- **OrderForm:** valinta contract/spot, "Laske hinta" -painike ja ehdotettujen rivien taulukko hyväksyntää varten.
- **TripDetail → Kustannukset:** automaattirivit merkitään ikonilla, ja info-rivit näytetään himmennettyinä.
- **Raportit:** kate- ja kattavuusnäkymät.

---

## 16. Esimerkkilaskelma (demodata)

**Tilaus:** asiakas *Nordic Demo Plastics Oy*, FI → BE, FTL, sopimushinta, maksullinen paino 22 000 kg.

| Koodi | Rivi | Peruste | Myynti € |
|---|---|---|---|
| 120 | Rahti | hinnasto FI → BE FTL | 2 000,00 |
| 200 | Polttoainelisä | sopimus 25 % | 500,00 |
| 230 | Liikkuvuuspaketti | listahinta BE 9 % | 180,00 |
| 530 | ETS-lisä | listahinta 150 € | 150,00 |
| | **Yhteensä** | | **2 830,00** |

**Trip** (yksi tilaus, koko kuorma):

| Koodi | Rivi | Kulu € |
|---|---|---|
| 210 | Kotimaan ajo, kuormattu 110 km × 1,20 | 132,00 |
| 211 | Kotimaan ajo, tyhjä 40 km × 1,00 | 40,00 |
| 212 | Kotimaan vetoyksikkö | 60,00 |
| 220 | Mantereen ajo, kuormattu 1 000 km × 0,40 | 400,00 |
| 221 | Mantereen ajo, tyhjä 120 km × 0,35 | 42,00 |
| 222 | Mantereen vetoyksikkö | 90,00 |
| 500 | Lautta | 1 010,00 |
| 520 | BAF | 300,00 |
| 530 | ETS | 180,00 |
| 400 | Trailervuokra 6 pv × 42 | 252,00 |
| | **Yhteensä** | **2 506,00** |

Empty % = 160 / 1 270 km = **12,6 %**

**Kate:** 2 830,00 − 2 506,00 = **324,00 € (11,4 %)**

**Kattavuus:** ETS myynti 150 € vs. kulu 180 € → **−30 €**. Asiakkaan ETS-lisää kannattaa tarkistaa.

---

## 17. Toteutusvaiheet

Jokainen vaihe on oma haaransa ja omat testinsä. Vaiheet 1–6 ovat backendiä ja sopivat pilvi-istuntoon.

| # | Vaihe | Hyväksymiskriteerit |
|---|---|---|
| 1 | services-taulu + koodiston yhtenäistäminen | Koodisto haetaan kannasta, 401/831 yhdistetty, vanhat rivit migroitu, testit vihreänä |
| 2 | surcharge_rates + laskentafunktio | Kaikki 4 rate_typeä, min/max, hakujärjestys ja voimassaolo testattu |
| 3 | Polttoainelisän siirto | fuel_rates → surcharge_rates, 120 → 200 -automaatti toimii kuten ennen |
| 4 | Asiakashinnasto + lisäsäännöt (API) | CRUD-endpointit, haku postinumeroalueella ja maalla testattu |
| 5 | Tilauksen hinnanmuodostus (API) | price-preview ja price-apply, contract ja spot, trade_type-päättely testattu |
| 6 | Tripin automaattikulut (API) | Trip-km-kentät, kuljetusyhtiökohtaiset km-hinnat, rivit 210–212 ja 220–222, lautta-, BAF- ja ETS-rivit; käsin muokattuja ei ylikirjoiteta |
| 7 | Käyttöliittymät | Hinnoittelu → Lisät, asiakaskortin välilehdet, OrderFormin hintaehdotus |
| 8 | Kate ja raportit | Kohdistus LDM:llä, margin- ja recovery-raportit |

---

## 18. Avoimet kysymykset

1. ~~**Tiemaksut**~~ **Ratkaistu:** tiemaksu lasketaan km:ien mukaan maittain. Myynti arvioiduista km:istä, kulu toteutuneista km:istä (`trip_country_km`).
2. ~~**Spot-info-lisien peruste**~~ **Ratkaistu:** info-rivien prosenttilisät lasketaan asiakkaan hinnaston sopimusrahdista, jos reitille löytyy hinta, muuten spot-hinnasta. Spot-hinta sisältää jo lisät, joten sen käyttö perusteena laskisi ne kahteen kertaan.
3. ~~**Kohdistusperuste**~~ **Ratkaistu:** kulut kohdistetaan LDM-osuuden mukaan. LDM on tilauksella pakollinen tieto (vähintään arvio), joten OrderForm vaatii sen. Paino on varalla vain vanhoille tilauksille, joilta LDM puuttuu.

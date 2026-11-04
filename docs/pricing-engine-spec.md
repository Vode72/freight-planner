# Hinnoittelumoottori — määrittely

**Projekti:** Freight Planner (TMS)
**Versio:** 1.1 (11/2026)
**Tila:** Hyväksytty toteutettavaksi

> Kaikki tämän dokumentin koodit, hinnat, prosentit ja asiakkaat ovat keksittyä demodataa.

**Muutokset versiossa 1.1**

| # | Muutos | Luku |
|---|---|---|
| 1 | Lisähinnoilla pakollinen `cost_type` (toteutettu #3) | 7.2, 13 |
| 2 | Uusi rate_type `pass_through` asiakassääntöihin | 7.1, 8.2 |
| 3 | Maksaja `orders.payer_customer_id`, oletus toimitusehdosta; osapuolet linkitetty tunnisteilla `consignor_customer_id` / `consignee_customer_id` | 8.3, 9, 13 |
| 4 | Mantereen vetäjä `trips.continent_carrier_id` + `continent_truck_plate` | 10.1 |
| 5 | Tyhjän ajon määritelmä ja kohdistus (kotimaa `truck_plate`, manner `continent_truck_plate`) | 10.2 |
| 6 | Trailervuokran uudelleenlaskenta toteutuneilla päivillä | 10.3 |
| 7 | Lukitun keikan korjaus vastakirjauksella (`costs.reversal_of_id`) | 11.2 |
| 8 | `costs.created_by` ja `costs.reversed_by` | 11.2, 13 |
| 9 | Recovery: myynti ilman vastaavaa kulua → "sisältyy muihin kuluihin" | 12 |
| 10 | Käyttöliittymä: TripDetailin ja OrderDetailin välilehdet | 15 |
| 11 | Uusi luku Käyttöoikeudet | 16 |
| 12 | Rajaukseen: arvio vs. toteuma, jaksotukset, kalustoluokka | 2 |
| 13 | Kertaluonteiset migraatiot `schema_migrations`-tauluun (toteutettu #4) | 4, 13 |
| 14 | Asiakashinnasto ja lisäsäännöt (toteutettu #5); luvun 8.2 esimerkki koskee Baltic Demo Tradingia | 8, 13, 14 |

Luvusta 16 alkaen numerointi siirtyi yhdellä (Esimerkkilaskelma on nyt luku 17).

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
- Valuutat (kaikki euroina)
- Arvio vs. toteuma: keikan ennakoitujen ja toteutuneiden kulujen vertailuraportti (rivit tallennetaan vain toteutuneina; poikkeus: tiemaksun km-arvio, luku 10)
- Jaksotukset: tuottojen ja kulujen kohdistaminen kirjanpitokausille (kate raportoidaan keikan päivämäärällä)
- Kalustoluokka: akselimäärä ja päästöluokka eivät vaikuta km-hintoihin eivätkä tiemaksuihin

Maakohtainen km-jakauma reitiltä toteutetaan erikseen (#13, OpenRouteService). Siihen asti km:t syötetään käsin.

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
| Läpilaskutus (pass_through) | Myynti = tripin toteutunut kulu samalla koodilla, valinnaisesti kate-% päälle |
| Maksaja (payer) | Asiakas, jonka hinnastolla ja lisäsäännöillä tilaus hinnoitellaan ja jolle se laskutetaan |
| Tyhjä ajo | Siirtymä edellisen keikan purkupaikalta tämän keikan lastauspaikalle |
| Vastakirjaus | Lukitun rivin korjaus: alkuperäisen rivin miinusrivi + uusi oikea rivi |

---

## 4. Periaatteet

1. **Koodi = palvelu, cost_type = suunta.** Sama koodi esiintyy sekä osto- että myyntirivillä. Vanhat koodiparit yhtenäistetään (401 → 400, 831 → 830).
2. **Voimassaolo kaikessa.** Jokaisella hinnalla on `valid_from` ja `valid_to`. Riville tallennetaan tilauksen päivämäärän mukainen hinta, joten hinnan muuttuminen ei muuta vanhoja tilauksia.
3. **Tarkin sääntö voittaa.** Asiakassopimus ohittaa listahinnan. Maakohtainen hinta ohittaa aluehinnan.
4. **Ihminen hyväksyy.** Järjestelmä ehdottaa rivit, ja dispatcher voi muokata, poistaa tai lisätä ennen tallennusta.
5. **Ei kertautuvia lisiä.** Prosenttilisät lasketaan aina pelkästä rahtirivistä, ei toisten lisien päälle.
6. **Trippi kantaa kulut, tilaus kantaa myynnin.** Tripin kulut kohdistetaan tilauksille katelaskentaa varten.
7. **Pyöristys:** kaksi desimaalia, puolikkaat ylöspäin, jokainen rivi erikseen.
8. **Laskutettua ei muuteta.** Lukitun keikan rivejä ei muokata eikä poisteta; korjaus tehdään vastakirjauksella (luku 11.2).
9. **Jäljitettävyys.** Jokaisella kulu- ja myyntirivillä on tekijä (`created_by`), ja vastakirjatulla rivillä vastakirjaaja (`reversed_by`).
10. **Kertaluonteiset migraatiot kirjataan.** Datan siirrot, joita ei saa ajaa kahdesti (esim. polttoainelisän siirto), merkitään `schema_migrations`-tauluun. Migraatio tarkistaa merkinnän ennen ajoa (toteutettu #4).

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
| `pass_through` | tripin toteutunut kulu samalla koodilla × (1 + kate-%) | Satamamaksu läpilaskutettuna + 5 % |

Jokaisella rivillä voi olla `min_amount` ja `max_amount`.

`pass_through` on sallittu **vain asiakkaan lisäsäännöissä** (`customer_billing_rules`, luku 8.2). Listahinnoissa (`surcharge_rates`) sitä ei hyväksytä, koska läpilaskutus on aina asiakaskohtainen sopimus.

### 7.2 Kohdistus

Jokaisella lisähintarivillä on **pakollinen `cost_type`** (`revenue` = myynti asiakkaalle, `cost` = osto operaattorilta). Sama lisä on usein eri hintainen myynnissä ja ostossa (esim. ETS myynti 150 €, kulu 180 €), joten haussa `cost_type` on aina annettava eikä sitä voi jättää tyhjäksi (toteutettu #3). Puuttuva `cost_type` → virhe.

Lisäksi hinta voi kohdistua seuraavien yhdistelmään (tyhjä = kaikki):
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

Haku tehdään aina saman `cost_type`n sisällä. Jos samalla kohdistuksella ja suunnalla on päällekkäin voimassa olevia rivejä, tallennus hylätään (API 409).

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

Nykyinen `fuel_rates.multiplier` siirretään `surcharge_rates`-tauluun prosenttina: `rate = (multiplier − 1) × 100` (`cost_type = revenue`). Siirto on kertaluonteinen ja merkitään `schema_migrations`-tauluun, joten uudelleenajo ei kopioi rivejä (toteutettu #4). FuelRateManager-näkymä korvataan Hinnoittelu → Lisät -välilehdellä.

---

## 8. Asiakashinnoittelu

Hinnasto ja lisäsäännöt haetaan aina tilauksen **maksajan** (`payer_customer_id`, luku 8.3) mukaan, ei lähettäjän tai vastaanottajan.

### 8.1 Hinnasto (`customer_rate_cards`)
Asiakkaan sovitut rahtihinnat reiteittäin:
- lähtömaa ja valinnainen postinumeroalue
- kohdemaa ja valinnainen postinumeroalue
- product_type
- rahtihinta (€)
- voimassaolo

Haku: tarkin postinumeroalueosuma ensin, sitten pelkkä maa (toteutettu #5). Postinumeroalue on postinumeron alku (esim. `33` = Tampereen seutu); osuma molemmissa päissä voittaa osuman yhdessä päässä, ja pidempi alue lyhyemmän. Postinumeron alussa oleva maakoodi ohitetaan (`LV-1050` = `1050`).

### 8.2 Lisäsäännöt (`customer_billing_rules`)
Asiakaskohtaisesti jokaiselle lisälle:
- `billed`: laskutetaanko lisä asiakkaalta (kyllä/ei)
- valinnainen oma hinta (`rate_type` + `rate`: percent, fixed, per_100kg, per_km tai pass_through), muuten listahinta
- voimassaolo

Esimerkki: *Baltic Demo Trading Oy* maksaa rahdin, polttoainelisän 22 % (sopimus) ja ETS-lisän listahinnalla. Liikkuvuuspakettia ei laskuteta erikseen (`billed = false`), ja satamamaksu läpilaskutetaan 5 % katteella. (Luvun 17 *Nordic Demo Plastics Oy* maksaa sen sijaan liikkuvuuspaketin listahinnalla.)

Jos asiakkaalla ei ole sääntöä lisälle, käytetään listahintaa. Sääntö ilman omaa hintaa (`rate_type` tyhjä) tarkoittaa listahintaa, ja `billed = false` ei salli omaa hintaa.

**Läpilaskutus (`pass_through`):** myyntirivi = tripin toteutuneet kulurivit samalla palvelukoodilla, kerrottuna `(1 + rate / 100)`. `rate` on valinnainen kate-%; tyhjä = 0 % eli kulu sellaisenaan.

- Tripin yhteiset kulut (`order_id` tyhjä) kohdistetaan tilaukselle LDM-osuuden mukaan (luku 11), tilauskohtaiset kulut suoraan.
- Jos kulua ei vielä ole kirjattu, riviä ei ehdoteta ja hintaehdotuksessa on varoitus. Rivi lasketaan uudelleen, kun kulu kirjataan, kunnes keikka laskutetaan (käsin muokattuja rivejä ei ylikirjoiteta).
- Esimerkki: satamamaksu 510, kulu 120 €, kate 5 % → myynti 126,00 €.

### 8.3 Maksaja (`orders.payer_customer_id`)

Tilauksella on maksaja, jonka hinnastolla ja lisäsäännöillä se hinnoitellaan. Oletus päätellään toimitusehdosta (`orders.incoterms`):

| Toimitusehto | Maksaja (oletus) |
|---|---|
| DAP, DDP, CPT, CIP | lähettäjä (consignor) |
| EXW, FCA | vastaanottaja (consignee) |
| muu tai tyhjä | ei oletusta, valitaan käsin |

- Lähettäjä ja vastaanottaja linkitetään asiakasrekisteriin tunnisteilla `orders.consignor_customer_id` ja `orders.consignee_customer_id`. OrderFormin automaattitäydennys tallentaa valitun asiakkaan tunnisteen nimen ja osoitteen lisäksi.
- Oletus päätellään **tunnisteista, ei nimistä**: lähettäjä → `consignor_customer_id`, vastaanottaja → `consignee_customer_id`.
- Oletus asetetaan, kun tilaus luodaan tai toimitusehto vaihtuu, jos dispatcher ei ole valinnut maksajaa käsin.
- Maksaja on aina muokattavissa OrderFormissa (asiakasrekisterin asiakas).
- Jos oletuksen mukainen tunniste on tyhjä (osapuoli ei ole rekisterissä), maksaja jää tyhjäksi ja "Laske hinta" pyytää valitsemaan sen.
- **Vanhat tilaukset:** kertaluonteinen migraatio (kirjataan `schema_migrations`-tauluun) linkittää `consignor_name`/`consignee_name` asiakkaaseen vain, kun nimi vastaa asiakkaan nimeä täsmälleen. Muut jäävät tyhjiksi.
- Maksajan vaihto ei muuta jo tallennettuja rivejä; hinta lasketaan uudelleen "Laske hinta" -painikkeella.

---

## 9. Hinnanmuodostus tilaukselle

```
Tilaus tallennetaan / dispatcher painaa "Laske hinta"
  │
  ├─ Päättele trade_type (lastaus- ja purkumaa)
  ├─ Maksaja: payer_customer_id (oletus toimitusehdosta, luku 8.3)
  ├─ pricing_type?
  │   ├─ contract → hae rahti (120) maksajan hinnastosta
  │   └─ spot     → dispatcher syöttää hinnan (100)
  ├─ Käy läpi kaikki lisät:
  │   ├─ maksajan sääntö → billed? oma hinta? pass_through?
  │   └─ muuten listahinta hakujärjestyksellä (cost_type = revenue)
  ├─ contract → lisät invoice-riveiksi
  │  spot     → lisät info-riveiksi
  └─ Näytä ehdotus → dispatcher muokkaa / hyväksyy → tallennus
```

Tilaukselle tarvitaan uudet kentät: `pricing_type` (contract/spot), `product_type` (FTL/LTL), `chargeable_weight`, `consignor_customer_id`, `consignee_customer_id`, `payer_customer_id`.

---

## 10. Tripin kulut

Vetäjän kulut jaetaan sekä kotimaan että mantereen osuudella kolmeen osaan:

| Osuus | Kuormattu | Tyhjä | Vetoyksikkö |
|---|---|---|---|
| Kotimaa | 210 | 211 | 212 |
| Manner | 220 | 221 | 222 |

- **Kuormattu ajo:** lastauspaikalta purkupaikalle (tai satamaan / satamasta)
- **Tyhjä ajo:** siirtymä edellisen keikan purkupaikalta tämän keikan lastauspaikalle (luku 10.2)
- **Vetoyksikkö:** kiinteä osa per keikka

Hinnat ovat kuljetusyhtiökohtaisia, koska eri vetäjillä on eri sopimukset. Tyhjät km:t tuottavat samalla Empty % -mittarin (tyhjät km / kaikki km).

### 10.1 Kotimaan ja mantereen vetäjä

Lauttakeikalla kotimaan ja mantereen osuuden ajaa usein eri kuljetusyhtiö. Tripillä on siksi kaksi vetäjää:

| Osuus | Kuljetusyhtiö | Vetoyksikkö | Koodit |
|---|---|---|---|
| Kotimaa | `trips.carrier_id` | `trips.truck_plate` | 210–212 |
| Manner | `trips.continent_carrier_id` | `trips.continent_truck_plate` | 220–222 |

Km-hinnat haetaan kummankin vetäjän omasta hinnastosta (`km_rates.carrier_id`, tyhjä = oletushinta). Jos `continent_carrier_id` on tyhjä, mantereen osuus käyttää `carrier_id`:tä (sama vetäjä koko matkan).

### 10.2 Tyhjä ajo

Tyhjä ajo on siirtymä **edellisen keikan purkupaikalta tämän keikan lastauspaikalle**, ja sen kulu kohdistuu **lastattavalle keikalle** (sille keikalle, jota varten siirrytään).

- Edellinen keikka = saman vetoyksikön edellinen keikka lastauspäivän mukaan, kotimaa ja manner erikseen:
  - kotimaan osuus (211): saman `truck_plate`n edellinen keikka
  - mantereen osuus (221): saman `continent_truck_plate`n edellinen keikka
- Jos edellistä keikkaa ei ole, tyhjä ajo lasketaan vetäjän lähtöpisteestä tai syötetään käsin.
- Purkupaikan jälkeinen paluu ei kuulu purettavalle keikalle; se kirjataan seuraavalle keikalle, kun sellainen on.

### 10.3 Trailervuokra

Trailervuokra (400) lasketaan kahdessa vaiheessa:

1. **Vahvistus** (→ Vahvistettu): kulu- ja myyntirivi suunnitelluilla päivillä (nykyinen automaatti).
2. **Toimitus** (→ Toimitettu): rivit lasketaan uudelleen toteutuneilla päivillä FEC-kuittauksista (`loading_started_at` → `delivery_completed_at`, alkavat kalenteripäivät).

Uudelleenlaskenta päivittää vain automaattirivit (`is_auto = 1`). Käsin muokattuja rivejä ei ylikirjoiteta. Jos FEC-aikaleimat puuttuvat, suunnitellut päivät jäävät voimaan ja dispatcher saa ilmoituksen.

| Kulu | Lähde | Milloin |
|---|---|---|
| 210–212 / 220–222 vetäjän kulut | km_rates (kotimaa: carrier_id, manner: continent_carrier_id) × trip-km:t | km syötetään tripille |
| 500 lautta | ferry_rates reitin mukaan | lauttareitti valitaan |
| 510 satamamaksu | ferry_rates / satama | lauttareitti valitaan |
| 520 BAF, 530 ETS | surcharge_rates operaattorin mukaan | lauttareitti valitaan |
| 300–350 tiemaksut | surcharge_rates (per_km, maa) × toteutuneet km maittain | toteutuneet km syötetään |
| 400 trailervuokra | leasing_rate × päivät | trip vahvistetaan (suunnitellut päivät), uudelleen toimitettuna (FEC-päivät) |
| 800 odotus | FEC-kuittaus | lastaus > 30 min myöhässä (nykyinen) |

**Tiemaksut:** km:t kirjataan maittain (`trip_country_km`), sekä arvioidut että toteutuneet. Asiakkaan tiemaksulisä lasketaan tilauksella arvioiduista km:istä, koska hinta annetaan ennen ajoa. Kulurivi lasketaan toteutuneista km:istä, kun ne syötetään. Erotus näkyy kattavuusraportissa. Kalustoluokka (akselit, päästöluokka) ei vaikuta hintaan (rajaus, luku 2).

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

### 11.2 Korjaukset ja jäljitettävyys

Laskutettu keikka on lukittu: sen rivejä ei voi muokata eikä poistaa. Virhe korjataan **vastakirjauksella**:

1. Alkuperäiselle riville luodaan miinusrivi: sama koodi, `cost_type`, `order_id` ja `line_type`, summa negatiivisena, `reversal_of_id` = alkuperäisen rivin id.
2. Alkuperäiselle riville asetetaan `reversed_by` (vastakirjaaja). Rivi jää näkyviin, mutta se on merkitty vastakirjatuksi.
3. Tarvittaessa lisätään uusi, oikea rivi.

Rivi voidaan vastakirjata vain kerran, eikä miinusriviä voi vastakirjata. Alkuperäinen rivi ja sen miinusrivi kumoavat toisensa, joten kate ja raportit pysyvät oikeina ilman erillistä suodatusta. Vastakirjaus on sallittu vain laskuttajalle ja adminille (luku 16).

**Tekijätiedot:** jokaiselle `costs`-riville tallennetaan `created_by` (rivin luonut käyttäjä; automaattiriveillä se käyttäjä, jonka toimenpide rivin synnytti) ja vastakirjatulle riville `reversed_by`. Käyttäjät ja roolit toteutetaan #15:ssä; siihen asti kenttiin tallennetaan kirjautunut demokäyttäjä.

---

## 12. Raportointi

| Näkymä | Kysymys |
|---|---|
| Margin by Order | Kannattaako tämä tilaus? |
| Margin by Trip | Kannattaako tämä keikka kokonaisuutena? |
| Surcharge recovery | Kattaako asiakkaalta peritty ETS/BAF/polttoaine todellisen kulun? Vertailu samalla koodilla myynti vs. kulu. |
| Spot vs. contract | Myytiinkö spot listahintaa kalliimmalla vai halvemmalla? |
| Asiakas- ja reittikate | Kannattavimmat ja heikoimmat asiakkaat ja kohdemaat |

**Recovery: myynti ilman vastaavaa kulua.** Jos koodilla on myyntiä mutta keikalla ei ole samaa koodia kuluna (esim. 230 liikkuvuuspaketti, joka sisältyy vetäjän km-hintaan, tai 720 hallinnointimaksu), rivi näytetään tilassa **"sisältyy muihin kuluihin"**. Sitä ei näytetä 100 %:n katteena eikä alikattavuutena, eikä se vaikuta kattavuusprosenttiin. Kulu ilman myyntiä näytetään tavallisena alikattavuutena.

Nämä toimivat myöhemmin Power BI -integraation datalähteenä.

---

## 13. Tietomalli

**Uudet taulut**

```
services
  code (PK), name, category, default_cost_type, active

surcharge_rates
  id, service_code, cost_type (pakollinen), trade_type, product_type,
  country, operator, rate_type, rate, min_amount, max_amount,
  valid_from, valid_to

customer_rate_cards
  id, customer_id, origin_country, origin_zip_prefix,
  dest_country, dest_zip_prefix, product_type, freight_price,
  valid_from, valid_to

customer_billing_rules
  id, customer_id, service_code, billed,
  rate_type (percent/fixed/per_100kg/per_km/pass_through), rate,
  valid_from, valid_to

trip_country_km
  id, trip_id, country, estimated_km, realized_km

schema_migrations
  name (PK), applied_at           -- kertaluonteiset migraatiot (#4)

users                             -- #15, luku 16
  id, username, name, role, active, password_hash
```

**Muutokset olemassa oleviin**

```
orders:   + pricing_type, product_type, chargeable_weight,
            consignor_customer_id, consignee_customer_id,
            payer_customer_id (→ customers)
costs:    + order_id (nullable), line_type (invoice/info), is_auto,
            reversal_of_id (→ costs, nullable),
            created_by, reversed_by (→ users, nullable)
trips:    + domestic_loaded_km, domestic_empty_km,
            continent_loaded_km, continent_empty_km,
            continent_carrier_id (→ carriers), continent_truck_plate
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
POST   /api/costs/:id/reverse          → miinusrivi (+ valinnainen uusi rivi)

GET    /api/trips/:id/margin           → myynti tilauksittain, kate koodeittain + kohdistus
GET    /api/orders/:id/costing         → myynti vs. kohdistetut kulut

GET    /api/reports/margin             ?level=order|trip|customer|country
GET    /api/reports/surcharge-recovery ?from=&to=
```

---

## 15. Käyttöliittymä

- **Hallinta → Hinnoittelu:** uusi välilehti *Lisät* (surcharge_rates, aluesyöttö, voimassaolon tila). Polttoaine-välilehti yhdistetään tähän.
- **Asiakaskortti:** välilehdet *Perustiedot*, *Hinnasto*, *Lisät*.
- **OrderForm:** valinta contract/spot, maksaja (oletus toimitusehdosta), "Laske hinta" -painike ja ehdotettujen rivien taulukko hyväksyntää varten.
- **TripDetail**, välilehdet:
  - *Kulut:* tripin kulurivit; automaattirivit ikonilla, info-rivit himmennettyinä, vastakirjatut ja miinusrivit merkittyinä.
  - *Myynti:* myyntirivit tilauksittain, tilauskohtaiset välisummat.
  - *Kate:* myynti, kulu ja kate koodeittain sekä yhteisten kulujen kohdistus tilauksille (LDM-osuus, luku 11).
- **OrderDetail** (uusi), välilehdet:
  - *Hinnoittelu:* tilauksen myyntirivit, hinnoittelutapa, maksaja ja hintaehdotus.
  - *Costing:* tilauksen myynti vs. sille kohdistetut kulut (yhteiset LDM-osuudella + tilauskohtaiset) ja tilauksen kate.
- **Raportit:** kate- ja kattavuusnäkymät.

Tripin sisäistä hyvityspeilausta (myyntirivin automaattinen peilaus hyvitykseksi keikan sisällä) ei toteuteta; korjaukset tehdään vastakirjauksella (luku 11.2).

---

## 16. Käyttöoikeudet

Käyttäjät ja roolit toteutetaan #15:ssä. Oikeus tarkistetaan backendissä jokaisessa kirjoittavassa endpointissa dekoraattorilla; frontend piilottaa lisäksi toiminnot, joihin roolilla ei ole oikeutta. Kielletty toiminto → 403.

| Toiminto | dispatcher | laskuttaja | hinnoittelija | esihenkilö | admin |
|---|---|---|---|---|---|
| Tilaukset ja keikat (luonti, muokkaus) | ✔ | katselu | katselu | katselu | ✔ |
| Kulu- ja myyntirivit ennen laskutusta | ✔ | ✔ | katselu | katselu | ✔ |
| Laskutus, lukitus ja vastakirjaus | – | ✔ | – | – | ✔ |
| Hinnastot ja lisähinnat | katselu | katselu | ✔ | katselu | ✔ |
| Raportit | katselu | ✔ | ✔ | ✔ | ✔ |
| Käyttäjät | – | – | – | – | ✔ |
| Muut näkymät | katselu | katselu | katselu | katselu | ✔ |

- ✔ = täysi oikeus, katselu = vain luku, – = ei oikeutta (toiminto piilotetaan, backend palauttaa 403).
- `created_by` ja `reversed_by` (luku 11.2) täytetään kirjautuneesta käyttäjästä.
- Demossa kirjautumissivulla on roolinvaihto (demokäyttäjä per rooli).

---

## 17. Esimerkkilaskelma (demodata)

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

## 18. Toteutusvaiheet

Jokainen vaihe on oma haaransa ja omat testinsä. Vaiheet 1–6 ja 9–11 ovat pääosin backendiä ja sopivat pilvi-istuntoon.

| # | Issue | Vaihe | Hyväksymiskriteerit |
|---|---|---|---|
| 1 | #2 ✅ | services-taulu + koodiston yhtenäistäminen | Koodisto haetaan kannasta, 401/831 yhdistetty, vanhat rivit migroitu, testit vihreänä |
| 2 | #3 ✅ | surcharge_rates + laskentafunktio | Kaikki 4 rate_typeä, pakollinen cost_type, min/max, hakujärjestys ja voimassaolo testattu |
| 3 | #4 ✅ | Polttoainelisän siirto | fuel_rates → surcharge_rates, 120 → 200 -automaatti toimii kuten ennen, siirto kirjattu schema_migrations-tauluun |
| 4 | #5 ✅ | Asiakashinnasto + lisäsäännöt (API) | CRUD-endpointit, haku postinumeroalueella ja maalla testattu |
| 5 | #6 | Tilauksen hinnanmuodostus (API) | price-preview ja price-apply, contract ja spot, trade_type-päättely, maksaja toimitusehdosta, pass_through, created_by testattu |
| 6 | #7 | Tripin automaattikulut (API) | Trip-km-kentät, kotimaan ja mantereen vetäjän km-hinnat, rivit 210–212 ja 220–222, tyhjä ajo lastattavalle keikalle, lautta-, BAF- ja ETS-rivit, trailervuokran uudelleenlaskenta FEC-päivillä, vastakirjaus; käsin muokattuja ei ylikirjoiteta |
| 7 | #8 | Käyttöliittymät | Hinnoittelu → Lisät, asiakaskortin välilehdet, OrderFormin hintaehdotus, TripDetailin ja OrderDetailin välilehdet (luku 15) |
| 8 | #9 | Kate ja raportit | Kohdistus LDM:llä, margin- ja recovery-raportit, "sisältyy muihin kuluihin" |
| 9 | #13 | Km:t kartalta (OpenRouteService) | Reitti rekkaprofiililla lauttasatamien kautta, km maittain trip_country_km-tauluun, välimuisti, mock-testit, käsisyöttö varalla |
| 10 | #14 | Demodata realistiseksi + freight.db pois versionhallinnasta | Yksi komento puhtaaseen demokantaan, katteet 8–20 %, DB-polku ympäristömuuttujasta, migrate_db() vain käynnistyksessä, testit eivät koske freight.db:hen |
| 11 | #15 | Käyttäjät ja roolit | users-taulu, roolit ja oikeusmatriisi (luku 16), dekoraattoritarkistus, 403-testit jokaiselle roolille |

---

## 19. Avoimet kysymykset

1. ~~**Tiemaksut**~~ **Ratkaistu:** tiemaksu lasketaan km:ien mukaan maittain. Myynti arvioiduista km:istä, kulu toteutuneista km:istä (`trip_country_km`).
2. ~~**Spot-info-lisien peruste**~~ **Ratkaistu:** info-rivien prosenttilisät lasketaan asiakkaan hinnaston sopimusrahdista, jos reitille löytyy hinta, muuten spot-hinnasta. Spot-hinta sisältää jo lisät, joten sen käyttö perusteena laskisi ne kahteen kertaan.
3. ~~**Kohdistusperuste**~~ **Ratkaistu:** kulut kohdistetaan LDM-osuuden mukaan. LDM on tilauksella pakollinen tieto (vähintään arvio), joten OrderForm vaatii sen. Paino on varalla vain vanhoille tilauksille, joilta LDM puuttuu.

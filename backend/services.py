"""Palvelukoodisto (services-taulu).

Koodi = palvelu, cost_type = suunta. Sama koodi voi esiintyä sekä osto-
(cost) että myyntirivillä (revenue); default_cost_type on vain oletus,
jota käyttöliittymä ehdottaa uudelle riville.

Kaikki koodit ovat keksittyjä demokoodeja.
"""

# (code, name, category, default_cost_type)
SERVICES = [
    # Rahti
    ("100", "SPOT", "rahti", "revenue"),
    ("120", "FREIGHT", "rahti", "revenue"),
    ("200", "POLTTOAINELISÄ", "rahti", "revenue"),
    ("210", "KOTIMAAN AJO, KUORMATTU", "rahti", "cost"),
    ("211", "KOTIMAAN AJO, TYHJÄ", "rahti", "cost"),
    ("212", "KOTIMAAN VETOYKSIKKÖ", "rahti", "cost"),
    ("220", "MANTEREEN AJO, KUORMATTU", "rahti", "cost"),
    ("221", "MANTEREEN AJO, TYHJÄ", "rahti", "cost"),
    ("222", "MANTEREEN VETOYKSIKKÖ", "rahti", "cost"),
    ("230", "LIIKKUVUUSPAKETTILISÄ", "rahti", "revenue"),
    # Tiemaksut
    ("300", "SAKSAN TIEMAKSU", "tiemaksut", "cost"),
    ("310", "HOLLANTI + SAKSA TIEMAKSU", "tiemaksut", "cost"),
    ("320", "ITÄVALLAN TIEMAKSU", "tiemaksut", "cost"),
    ("330", "RANSKAN TIEMAKSU", "tiemaksut", "cost"),
    ("340", "SVEITSIN TIEMAKSU", "tiemaksut", "cost"),
    ("350", "PUOLAN TIEMAKSU", "tiemaksut", "cost"),
    # Kalusto
    ("400", "TRAILERVUOKRA", "kalusto", "cost"),
    ("410", "TRAILERIN TANKKAUS", "kalusto", "cost"),
    ("830", "TRAILERIN YLIKÄYTTÖ", "kalusto", "cost"),
    # Lautta
    ("500", "LAUTTA", "lautta", "cost"),
    ("510", "SATAMAMAKSU", "lautta", "cost"),
    ("520", "BUNKKERILISÄ (BAF)", "lautta", "cost"),
    ("530", "PÄÄSTÖKAUPPALISÄ (ETS)", "lautta", "cost"),
    ("540", "MARPOL-LISÄ", "lautta", "cost"),
    # Lisät
    ("600", "ADR-LISÄ", "lisat", "cost"),
    ("610", "LÄMPÖTILALISÄ", "lisat", "cost"),
    ("700", "KÄSITTELYMAKSU", "lisat", "cost"),
    ("720", "HALLINNOINTIMAKSU", "lisat", "revenue"),
    ("799", "MUUT KULUT", "lisat", "cost"),
    ("800", "ODOTUSAIKA", "lisat", "cost"),
    ("810", "LISÄKÄSITTELY", "lisat", "cost"),
    ("820", "MUU KULU", "lisat", "cost"),
]

# Vanha koodi → yhtenäistetty koodi
LEGACY_CODE_MAP = {"401": "400", "831": "830"}


def ensure_services(conn):
    """Luo services-taulun ja täyttää koodiston. Idempotentti.

    Uudet koodit lisätään ja nimet/kategoriat/oletustyypit päivitetään,
    mutta käyttäjän asettamaan active-arvoon ei kosketa.
    """
    conn.execute("""
CREATE TABLE IF NOT EXISTS services (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    default_cost_type TEXT NOT NULL DEFAULT 'cost'
        CHECK (default_cost_type IN ('cost', 'revenue')),
    active INTEGER NOT NULL DEFAULT 1
)
""")
    conn.executemany(
        """
        INSERT INTO services (code, name, category, default_cost_type, active)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(code) DO UPDATE SET
            name = excluded.name,
            category = excluded.category,
            default_cost_type = excluded.default_cost_type
        """,
        SERVICES,
    )
    # Yhdistetyt vanhat koodit eivät kuulu koodistoon
    conn.executemany(
        "DELETE FROM services WHERE code = ?",
        [(old,) for old in LEGACY_CODE_MAP],
    )


def merge_legacy_codes(conn):
    """Migroi costs-rivit vanhoista koodeista (401, 831) uusiin (400, 830).

    cost_type, summa ja kuvaus säilyvät. Palauttaa muutettujen rivien määrän.
    """
    has_costs = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='costs'"
    ).fetchone()
    if not has_costs:
        return 0
    changed = 0
    for old, new in LEGACY_CODE_MAP.items():
        cur = conn.execute(
            "UPDATE costs SET cost_code = ? WHERE cost_code = ?", (new, old)
        )
        changed += cur.rowcount
    return changed


def run_services_migration(conn):
    ensure_services(conn)
    return merge_legacy_codes(conn)

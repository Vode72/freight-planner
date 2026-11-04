"""Tietokantapolun määritys.

Polku luetaan ympäristömuuttujasta FREIGHT_DB_PATH. Oletus on
backend/freight.db (absoluuttinen polku tämän tiedoston sijainnista),
joten skriptit toimivat riippumatta työhakemistosta.
"""
import os

DB_PATH_ENV = "FREIGHT_DB_PATH"
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "freight.db")


def get_db_path():
    return os.environ.get(DB_PATH_ENV) or DEFAULT_DB_PATH

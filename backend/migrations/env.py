"""Alembic-ympäristö (raaka sqlite3, ei ORM-metadataa).

Yhteys tulee joko db_migrate-moduulilta (config.attributes["connection"])
tai komentoriviltä: `alembic -x db=polku upgrade head`, oletuksena
db_config.get_db_path().
"""
import os
import sqlite3
import sys
from logging.config import fileConfig

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_config import get_db_path  # noqa: E402
from db_migrate import make_engine  # noqa: E402

config = context.config

if config.config_file_name is not None and "connection" not in config.attributes:
    fileConfig(config.config_file_name)


def _configure_and_run(connection):
    context.configure(
        connection=connection,
        target_metadata=None,
        render_as_batch=True,       # SQLite: ALTER-operaatiot taulun uudelleenluonnilla
        transactional_ddl=True,     # koko upgrade yhtenä transaktiona
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline():
    raise RuntimeError("Offline-tilaa (--sql) ei tueta: migraatiot muuntavat dataa Pythonissa.")


def run_migrations_online():
    connection = config.attributes.get("connection")
    if connection is not None:
        _configure_and_run(connection)
        return

    db_path = context.get_x_argument(as_dictionary=True).get("db") or get_db_path()
    engine = make_engine(lambda: sqlite3.connect(db_path))
    try:
        with engine.connect() as connection:
            _configure_and_run(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

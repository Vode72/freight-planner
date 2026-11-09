"""Yhteensopivuuskääre: ajaa Alembic-migraatiot (alembic upgrade head).

Skeema ja viitedata ovat migrations/versions-revisioissa, demodata
init_db.seed_demo_data():ssa (python reset_demo.py).
"""
from db_migrate import upgrade_db


def run_migration(db_path):
    upgrade_db(db_path)
    print(f"{__name__}: alembic upgrade head valmis ({db_path}).")


if __name__ == "__main__":
    from db_config import get_db_path
    run_migration(get_db_path())

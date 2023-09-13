import sys
import os
import logging
from alembic.config import Config
from alembic import command
from datetime import datetime


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.db.database.connection_utilities import get_connection_string


def create_migration(connection_string):
    # Initialize the Alembic configuration
    alembic_cfg = Config()

    # Set the database URL in the Alembic configuration
    alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
    alembic_cfg.set_main_option("script_location", "src/db/database/migrations")

    migration_msg = f"migration {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

    logging.info(f"Generating migration: {migration_msg}")
    command.revision(alembic_cfg, autogenerate=True, message=migration_msg)


def run_migration(connection_string):
    # Initialize the Alembic configuration
    alembic_cfg = Config()

    # Set the database URL in the Alembic configuration
    alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
    alembic_cfg.set_main_option("script_location", "src/db/database/migrations")

    # Run the Alembic upgrade command
    command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    create_migration(get_connection_string())
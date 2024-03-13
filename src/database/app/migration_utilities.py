import sys
import os
import logging
from alembic.config import Config
from alembic import command
from datetime import datetime

from connection_utilities import get_connection_string


def create_migration(connection_string, migrations_dir="src/database/app/migrations"):
    # Initialize the Alembic configuration
    alembic_cfg = Config()

    # Set the database URL in the Alembic configuration
    alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
    alembic_cfg.set_main_option("script_location", migrations_dir)

    migration_msg = f"migration {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

    logging.info(f"Generating migration: {migration_msg}")
    command.revision(alembic_cfg, autogenerate=True, message=migration_msg)


def run_migration(connection_string, migrations_dir="migrations"):
    # Initialize the Alembic configuration
    alembic_cfg = Config()

    # Set the database URL in the Alembic configuration
    alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
    alembic_cfg.set_main_option("script_location", migrations_dir)

    # Run the Alembic upgrade command
    command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    connection_string = get_connection_string()
    # Port setting (based on where I'm hosting this thing)
    connection_string = connection_string.replace("5432", "5433")
    
    # Uncomment to create migration
    # create_migration(connection_string)
    
    # Uncomment to run migration
    # run_migration(connection_string, "src/database/app/migrations")

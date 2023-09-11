import logging
from alembic.config import Config
from alembic import command
from datetime import datetime


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

import os
import logging
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.database.app.migration_utilities import run_migration
from src.database.app.default_data import (
    create_admin_user,
    ensure_conversation_role_types,
    ensure_supported_source_control_providers,
)
from src.database.app.connection_utilities import get_connection_string


ERROR_MSG_ROLE_TYPES = "Error ensuring conversation role types are in the database: {}. You probably didn't run the `migration_utilities.create_migration()`"
ERROR_MSG_SOURCE_CONTROL = "Error ensuring supported source control providers are in the database: {}. You probably didn't run the `migration_utilities.create_migration()`"
ERROR_MSG_ADMIN_USER = "Error creating admin user: {}. You probably didn't run the `migration_utilities.create_migration()`"


def run_migration_scripts():
    run_migration(get_connection_string())


def create_pgvector_extension():
    # Create a new connection engine to the newly created database
    engine = create_engine(get_connection_string())

    # Enable the "vector" extension in the new database
    enable_extension_command = "CREATE EXTENSION IF NOT EXISTS vector;"

    with engine.connect() as conn:
        result = conn.execute(text(enable_extension_command))
        conn.commit()

        if result.rowcount == -1:
            print("Extension 'vector' was successfully enabled.")
        else:
            print("Failed to enable extension 'vector'.")

    print("PGVector extension successfully created")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    logging.info("Creating the PGVector extension and running migration scripts...")
    # Enable pgvector extension
    create_pgvector_extension()

    # Run migration scripts
    run_migration_scripts()

    # Populate default conversation role types
    try:
        logging.info("Ensuring conversation role types exist in the database")
        ensure_conversation_role_types()
    except Exception as e:
        logging.error(ERROR_MSG_ROLE_TYPES.format(e))

    try:
        logging.info(
            "Ensuring supported source control providers exist in the database"
        )
        ensure_supported_source_control_providers()
    except Exception as e:
        print(ERROR_MSG_SOURCE_CONTROL.format(e))

    try:
        logging.info("Creating admin user")
        create_admin_user()
    except Exception as e:
        logging.error(ERROR_MSG_ADMIN_USER.format(e))

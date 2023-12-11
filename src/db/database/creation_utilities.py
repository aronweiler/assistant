import os
from sqlalchemy import create_engine, text

from src.db.database.migration_utilities import run_migration
from src.db.database.connection_utilities import get_connection_string


class CreationUtilities:
    @staticmethod
    def run_migration_scripts():
        run_migration(get_connection_string())

    @staticmethod
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

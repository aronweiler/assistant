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

    



# @staticmethod
    # def create_database(self, database):
    #     # This is generally not used, since the database is created automatically when the container is started

    #     # Access the environment variables
    #     default_database = "postgres"  # The default database name
    #     host = os.environ.get("POSTGRES_HOST", "localhost")
    #     port = int(os.environ.get("POSTGRES_PORT", 5432))
    #     database = os.environ.get("POSTGRES_DB", "postgres")
    #     user = os.environ.get("POSTGRES_USER", "postgres")
    #     password = os.environ.get("POSTGRES_PASSWORD", "postgres")

    #     # Create the connection engine to the default "postgres" database
    #     self.default_engine = create_engine(
    #         f"postgresql://{user}:{password}@{host}:{port}/{default_database}"
    #     )

    #     # Set the isolation level to autocommit
    #     default_connection = self.default_engine.connect()

    #     try:
    #         default_connection.connection.set_isolation_level(0)

    #         # Create the main database (if it doesn't exist)
    #         create_database_command = f"CREATE DATABASE IF NOT EXISTS {database};"
    #         default_connection.execute(text(create_database_command))

    #         # Set the isolation level back to default (1)
    #         default_connection.connection.set_isolation_level(1)
    #     finally:
    #         # Close the connection to the default database
    #         default_connection.close()
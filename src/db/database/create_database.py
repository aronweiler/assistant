import os
import time
from dotenv import dotenv_values
import logging
from sqlalchemy import create_engine, text

# Load environment variables from db.env
config = dotenv_values("src/db/database/db.env")
if not config:
    logging.error("Could not load environment variables from db.env")

# Access the environment variables
host = "localhost"
port = int(config.get("POSTGRES_PORT", 5432))
default_database = "postgres"  # The default database name
database = config.get("POSTGRES_DB", "postgres")
user = config.get("POSTGRES_USER", "postgres")
password = config.get("POSTGRES_PASSWORD", "postgres")

# Step 1: Create the connection engine to the default "postgres" database
default_engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{default_database}")

# Step 2: Set the isolation level to autocommit
default_connection = default_engine.connect()
try:
    default_connection.connection.set_isolation_level(0)

    # Step 3: Create the main database (if it doesn't exist)
    create_database_command = f"CREATE DATABASE {database};"
    default_connection.execute(text(create_database_command))

    # Step 4: Set the isolation level back to default (1)
    default_connection.connection.set_isolation_level(1)
finally:
    # Step 5: Close the connection to the default database
    default_connection.close()

# Step 5.5: Wait for 3 seconds to allow the database to be created... because for some fing reason it doesn't work without this
time.sleep(3)

# Step 6: Create a new connection engine to the newly created database
engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{database}")

# Step 7: Enable the "vector" extension in the new database
enable_extension_command = "CREATE EXTENSION IF NOT EXISTS vector;"

with engine.connect() as conn:
    result = conn.execute(text(enable_extension_command))
    
    if result.rowcount == -1:
        print("Extension 'vector' was successfully enabled.")
    else:
        print("Failed to enable extension 'vector'.")

print("Database created successfully")


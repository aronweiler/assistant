import os
from alembic.config import Config
from alembic import command
from dotenv import load_dotenv
import logging
from datetime import datetime
from sqlalchemy import create_engine, text

# Load environment variables from db.env
if not load_dotenv("src/memory/long_term/db.env"):
    logging.error("Could not load environment variables from db.env")

# Access the environment variables
host = "localhost"
port = int(os.environ.get("POSTGRES_PORT", 5432))
database = os.environ.get("POSTGRES_DB", "postgres")
user = os.environ.get("POSTGRES_USER", "postgres")
password = os.environ.get("POSTGRES_PASSWORD", "postgres")

engine = create_engine(
    f"postgresql://{user}:{password}@{host}:{port}/{database}"
)

create_command = f"""DO $$ 
BEGIN 
    IF EXISTS (SELECT 1 FROM pg_database WHERE datname = '{database}') THEN 
        CREATE DATABASE IF NOT EXISTS {database};
        CREATE EXTENSION vector;    
    END IF; 
END $$;"""

with engine.connect() as conn:
    conn.execute(text(create_command.format(database=database)))
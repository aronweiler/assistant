import os
from alembic.config import Config
from alembic import command
from dotenv import dotenv_values
import logging
from datetime import datetime

# Load environment variables from db.env
config = dotenv_values("src/db/database/db.env")
if not config:
    logging.error("Could not load environment variables from db.env")

# Access the environment variables
host = config.get("POSTGRES_HOST", "localhost")
port = int(config.get("POSTGRES_PORT", 5432))
database = config.get("POSTGRES_DB", "postgres")
user = config.get("POSTGRES_USER", "postgres")
password = config.get("POSTGRES_PASSWORD", "postgres")

# Set the SQLAlchemy database URL
db_url = f"postgresql://{user}:{password}@localhost:{port}/{database}"

# Initialize the Alembic configuration
alembic_cfg = Config()

# Set the database URL in the Alembic configuration
alembic_cfg.set_main_option("sqlalchemy.url", db_url)
alembic_cfg.set_main_option("script_location", "src/db/database/migrations")

if __name__ == "__main__":
    # Call Alembic to generate the migration
    migration_msg = f"migration {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    command.revision(alembic_cfg, autogenerate=True, message=migration_msg)

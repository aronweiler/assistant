import os
import logging

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import func

from contextlib import contextmanager
from dotenv import load_dotenv

from enum import Enum

class SearchType(Enum):
    key_word = "key_word"
    similarity = "similarity"


class VectorDatabase:
    def __init__(self, db_env_location):
        if not load_dotenv(db_env_location):
            raise ValueError(
                "Could not load environment variables from db.env, memory will not work."
            )

        try:
            host = "localhost"
            port = int(os.environ.get("POSTGRES_PORT", 5432))
            database = os.environ.get("POSTGRES_DB", "postgres")
            user = os.environ.get("POSTGRES_USER", "postgres")
            password = os.environ.get("POSTGRES_PASSWORD", "postgres")

            engine = create_engine(
                f"postgresql://{user}:{password}@{host}:{port}/{database}"
            )

            self.Session = sessionmaker(bind=engine)

        except (Exception, psycopg2.Error) as error:
            raise ConnectionError("Error while connecting to PostgreSQL") from error

    @contextmanager
    def session_context(self, session):
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def eager_load(self, query, eager_load: list):
        for eager_load_item in eager_load:
            try:
                query = query.options(selectinload(eager_load_item))
            except Exception as e:
                logging.error(f"Could not eager load {eager_load_item} due to {e}")
                raise e

        return query

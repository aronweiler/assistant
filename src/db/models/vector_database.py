import os
import logging

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import func

from contextlib import contextmanager
from dotenv import load_dotenv, dotenv_values

from enum import Enum


class SearchType(Enum):
    key_word = "key_word"
    similarity = "similarity"


class VectorDatabase:
    def __init__(self, db_env_location):
        try:
            connection_string = VectorDatabase.get_connection_string(db_env_location)

            engine = create_engine(connection_string)

            self.Session = sessionmaker(bind=engine)

        except (Exception, psycopg2.Error) as error:
            raise ConnectionError("Error while connecting to PostgreSQL") from error

    @staticmethod
    def get_connection_string(db_env_location):
        config = dotenv_values(db_env_location)

        if not config:
            raise ValueError(
                "Could not load environment variables from db.env, database will not work."
            )

        host = "localhost"
        port = int(config.get("POSTGRES_PORT", 5432))
        database = config.get("POSTGRES_DB", "postgres")
        user = config.get("POSTGRES_USER", "postgres")
        password = config.get("POSTGRES_PASSWORD", "postgres")

        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        return connection_string

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

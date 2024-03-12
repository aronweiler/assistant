import logging
import os
import psycopg2
from enum import Enum
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, selectinload
from contextlib import contextmanager


def get_connection_string():
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = int(os.environ.get("POSTGRES_PORT", 5432))
    database = os.environ.get("POSTGRES_DB", "postgres")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")

    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"

    return connection_string


class SearchType(Enum):
    Keyword = "Keyword"
    Similarity = "Similarity"


class VectorDatabase:
    def __init__(self):
        try:
            self.connection_string = get_connection_string()

            engine = create_engine(
                self.connection_string, pool_size=100, max_overflow=20
            )

            self.Session = sessionmaker(bind=engine)

        except (Exception, psycopg2.Error) as error:
            raise ConnectionError("Error while connecting to PostgreSQL") from error
    

    @staticmethod
    def database_exists():
        try:
            connection_string = VectorDatabase.get_connection_string()
            engine = create_engine(connection_string)
            engine.connect()
            return True
        except Exception:
            return False

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
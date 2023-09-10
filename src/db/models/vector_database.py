import os
import logging
import openai

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
    def __init__(self):
        try:
            connection_string = VectorDatabase.get_connection_string()

            engine = create_engine(connection_string, pool_size=20, max_overflow=0)

            self.Session = sessionmaker(bind=engine)

        except (Exception, psycopg2.Error) as error:
            raise ConnectionError("Error while connecting to PostgreSQL") from error

    @staticmethod
    def get_connection_string():
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = int(os.environ.get("POSTGRES_PORT", 5432))
        database = os.environ.get("POSTGRES_DB", "postgres")
        user = os.environ.get("POSTGRES_USER", "postgres")
        password = os.environ.get("POSTGRES_PASSWORD", "postgres")

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
    
    def get_embedding(self, text: str, embedding_model="text-embedding-ada-002"):
        return openai.Embedding.create(input=[text], model=embedding_model)["data"][0][
            "embedding"
        ]

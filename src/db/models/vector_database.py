import logging
import openai

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, selectinload

from contextlib import contextmanager

from enum import Enum

from src.db.database.connection_utilities import get_connection_string
from src.db.database.models import ConversationRoleType

class SearchType(Enum):
    key_word = "key_word"
    similarity = "similarity"

class VectorDatabase:
    def __init__(self):
        try:
            self.connection_string = get_connection_string()

            engine = create_engine(self.connection_string, pool_size=20, max_overflow=0)

            self.Session = sessionmaker(bind=engine)

        except (Exception, psycopg2.Error) as error:
            raise ConnectionError("Error while connecting to PostgreSQL") from error

    def ensure_conversation_role_types(self):        
        with self.session_context(self.Session()) as session:
            role_types = ["system", "assistant", "user", "function", "error"]

            for role_type in role_types:
                existing_role = session.query(ConversationRoleType).filter_by(role_type=role_type).first()

                if existing_role is None:
                    session.add(ConversationRoleType(role_type=role_type))

            session.commit()

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

    def get_embedding(self, text: str, embedding_model="text-embedding-ada-002"):
        return openai.Embedding.create(input=[text], model=embedding_model)["data"][0][
            "embedding"
        ]

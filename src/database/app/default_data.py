import os
import sys
import logging


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from passlib.hash import pbkdf2_sha256 as hasher
from src.shared.database.schema.tables import (
    ConversationRoleType,
    SupportedSourceControlProvider,
    User,
)
from vector_database import VectorDatabase

SUPPORTED_SOURCE_CONTROL_PROVIDERS = ["GitHub", "GitLab"]


def create_admin_user():
    logging.info("Creating admin user")
    vector_database = VectorDatabase()
    with vector_database.session_context(vector_database.Session()) as session:

        email = os.getenv("ADMIN_EMAIL")
        password = os.getenv("ADMIN_PASSWORD", None)
        name = os.getenv("ADMIN_NAME")
        location = os.getenv("ADMIN_LOCATION")
        age = 999        
        
        logging.info(f"Creating admin user with email: {email}, name: {name}, location: {location}, age: {age}, password not None: {password is not None}")
        
        if password is None:
            logging.error("No admin password was provided, so the admin user will not be created")
            return
        
        password_hash = hasher.hash(password)

        # If the user already exists, don't create it again
        if session.query(User).filter_by(email=email).count() > 0:
            return

        session.add(
            User(
                email=email,
                name=name,
                location=location,
                age=age,
                password_hash=password_hash,
                session_id=None,
                session_created=None,
                is_admin=True,
                enabled=True,
            )
        )


def ensure_conversation_role_types():
    logging.info("Ensuring conversation role types exist in the database")
    vector_database = VectorDatabase()
    with vector_database.session_context(vector_database.Session()) as session:
        role_types = ["system", "assistant", "user", "function", "error"]

        existing_role = None
        for role_type in role_types:
            if session.query(ConversationRoleType).count() > 0:
                existing_role = (
                    session.query(ConversationRoleType)
                    .filter_by(role_type=role_type)
                    .first()
                )

            if existing_role is None:
                session.add(ConversationRoleType(role_type=role_type))

        session.commit()

    logging.info("Conversation role types exist in the database")


def ensure_supported_source_control_providers():
    logging.info("Ensuring supported source control providers exist in the database")

    vector_database = VectorDatabase()
    with vector_database.session_context(vector_database.Session()) as session:

        existing_provider = None
        for provider in SUPPORTED_SOURCE_CONTROL_PROVIDERS:
            if session.query(SupportedSourceControlProvider).count() > 0:
                existing_provider = (
                    session.query(SupportedSourceControlProvider)
                    .filter_by(name=provider)
                    .first()
                )

            if existing_provider is None:
                session.add(SupportedSourceControlProvider(name=provider))

        session.commit()

    logging.info("Supported source control providers exist in the database")

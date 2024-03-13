

import os
import sys
import logging


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.shared.database.schema.tables import ConversationRoleType, SupportedSourceControlProvider
from vector_database import VectorDatabase

SUPPORTED_SOURCE_CONTROL_PROVIDERS = ["GitHub", "GitLab"]


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

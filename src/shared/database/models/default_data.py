


from src.db.database.tables import ConversationRoleType, SourceControlProvider, SupportedSourceControlProvider
from src.db.models.vector_database import VectorDatabase
from src.integrations.shared import SUPPORTED_SOURCE_CONTROL_PROVIDERS


def ensure_conversation_role_types():
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
        
def ensure_supported_source_control_providers():
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

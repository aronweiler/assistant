from typing import List, Any
from uuid import UUID
from sqlalchemy.orm.attributes import InstrumentedAttribute

from src.db.database.tables import Conversation
from src.db.models.vector_database import VectorDatabase
from src.db.models.domain.conversation_model import ConversationModel


class Conversations(VectorDatabase):
    def create_conversation(
        self, id: UUID, conversation_summary: str, user_id: int
    ) -> ConversationModel:
        with self.session_context(self.Session()) as session:
            conversation_summary = conversation_summary.strip()

            conversation = Conversation(
                id=id, conversation_summary=conversation_summary, user_id=user_id
            )

            session.add(conversation)
            session.commit()

            return ConversationModel.from_database_model(conversation)

    def update_conversation_summary(
        self,
        conversation_id: UUID,
        conversation_summary: str,
        needs_summary: bool = False,
    ):
        with self.session_context(self.Session()) as session:
            conversation_summary = conversation_summary.strip()

            session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).update(
                {
                    Conversation.conversation_summary: conversation_summary,
                    Conversation.needs_summary: needs_summary,
                }
            )

            session.commit()

    def update_selected_code_repo(
        self, conversation_id: UUID, code_repo_id: int
    ) -> None:
        with self.session_context(self.Session()) as session:
            session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).update({Conversation.last_selected_code_repo: code_repo_id})
            session.commit()

    def update_conversation_collection(
        self,
        conversation_id: UUID,
        last_selected_collection_id: int,
    ):
        with self.session_context(self.Session()) as session:
            session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).update(
                {
                    Conversation.last_selected_collection_id: last_selected_collection_id,
                }
            )

            session.commit()

    def get_conversation(self, id: UUID) -> ConversationModel:
        with self.session_context(self.Session()) as session:
            query = session.query(
                Conversation.conversation_summary,
                Conversation.needs_summary,
                Conversation.last_selected_collection_id,
                Conversation.last_selected_code_repo,
                Conversation.user_id,
                Conversation.id,
                Conversation.is_deleted,
                Conversation.record_created,
            ).filter(Conversation.id == id)

            return ConversationModel.from_database_model(query.first())

    def get_conversation_by_user_id(self, user_id: int) -> List[ConversationModel]:
        with self.session_context(self.Session()) as session:
            query = session.query(
                Conversation.conversation_summary,
                Conversation.needs_summary,
                Conversation.last_selected_collection_id,
                Conversation.last_selected_code_repo,
                Conversation.user_id,
                Conversation.id,
                Conversation.is_deleted,
                Conversation.record_created,
            ).filter(Conversation.user_id == user_id, Conversation.is_deleted == False)

            return [ConversationModel.from_database_model(i) for i in query.all()]

    def delete_conversation(self, conversation_id: UUID) -> None:
        with self.session_context(self.Session()) as session:
            session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).update({Conversation.is_deleted: True})
            session.commit()

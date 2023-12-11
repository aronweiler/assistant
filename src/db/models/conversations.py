from typing import Union, List, Any
from uuid import UUID
from sqlalchemy.orm.attributes import InstrumentedAttribute

from src.db.database.models import ConversationMessage
from src.db.models.vector_database import VectorDatabase, SearchType

from src.db.models.domain.conversation_message_model import ConversationMessageModel


class Conversations(VectorDatabase):
    def add_conversation(self, conversation: ConversationMessageModel) -> ConversationMessageModel:
        with self.session_context(self.Session()) as session:
            conversation.message_text = conversation.message_text.strip()

            if len(conversation.message_text) == 0:
                return

            db_conversation = conversation.to_database_model()
            # db_conversation.embedding = self.get_embedding(
            #     conversation.message_text
            # )

            session.add(db_conversation)
            session.commit()

            return ConversationMessageModel.from_database_model(db_conversation)

    def delete_conversation(self, conversation_id: int) -> None:
        with self.session_context(self.Session()) as session:
            session.query(ConversationMessage).filter(
                ConversationMessage.id == conversation_id
            ).update({ConversationMessage.is_deleted: True})
            session.commit()

    def delete_conversation_by_interaction_id(self, conversation_id: UUID) -> None:
        with self.session_context(self.Session()) as session:
            session.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id
            ).update({ConversationMessage.is_deleted: True})
            session.commit()

    def search_conversations_with_user_id(
        self,
        search_query: str,
        search_type: SearchType,
        associated_user_id: int,
        conversation_id: Union[UUID, None] = None,
        top_k=10,
        return_deleted=False,
    ) -> List[ConversationMessageModel]:
        # TODO: Handle searching metadata... e.g. metadata_search_query: Union[str,None] = None

        with self.session_context(self.Session()) as session:
            # Before searching, pre-filter the query to only include conversations that match the single inputs
            query = session.query(ConversationMessage).filter(
                ConversationMessage.is_deleted == return_deleted,
                ConversationMessage.user_id == associated_user_id,
                ConversationMessage.conversation_id == conversation_id
                if conversation_id is not None
                else True,
            )

            if type(search_type) == str:
                search_type = SearchType(search_type)

            if search_type == SearchType.Keyword:
                # TODO: Do better key word search
                query = query.filter(
                    ConversationMessage.message_text.contains(search_query)
                ).limit(top_k)
            elif search_type == SearchType.Similarity:
                # Calculate the query embedding, then search for the nearest neighbors
                embedding = self.get_embedding(search_query)
                query = self._get_nearest_neighbors(
                    session, query, embedding, top_k=top_k
                )
            else:
                raise ValueError(f"Unknown search type: {search_type}")

            return [ConversationMessageModel.from_database_model(c) for c in query]

    def get_conversations_for_interaction(
        self, conversation_id: UUID, top_k: int = None, return_deleted=None
    ) -> List[ConversationMessageModel]:
        if return_deleted is None:
            return_deleted = False
        elif return_deleted is True:
            return_deleted = True

        with self.session_context(self.Session()) as session:
            query = (
                session.query(
                    ConversationMessage.id,
                    ConversationMessage.conversation_id,
                    ConversationMessage.message_text,
                    ConversationMessage.user_id,
                    ConversationMessage.id,
                    ConversationMessage.record_created,
                    ConversationMessage.conversation_role_type_id,
                    ConversationMessage.additional_metadata,
                    ConversationMessage.exception,
                    ConversationMessage.is_deleted,
                )
                .filter(
                    ConversationMessage.conversation_id == conversation_id,
                    (ConversationMessage.is_deleted == False)
                    if return_deleted == False
                    else True,
                )
                .order_by(ConversationMessage.id)
            )

            #query = super().eager_load(query, [Conversation.conversation_role_type])

            return [
                ConversationMessageModel.from_database_model(c) for c in query.limit(top_k)
            ]

    def get_conversations_for_user(
        self, associated_user_id: int, top_k: int = None
    ) -> List[ConversationMessageModel]:
        with self.session_context(self.Session()) as session:
            query = session.query(
                ConversationMessage.conversation_id,
                ConversationMessage.message_text,
                ConversationMessage.user_id,
                ConversationMessage.conversation_role_type,
                ConversationMessage.id,
                ConversationMessage.record_created,
                ConversationMessage.additional_metadata,
                ConversationMessage.exception,
                ConversationMessage.is_deleted,
            ).filter(ConversationMessage.user_id == associated_user_id)

            query = super().eager_load(query, [ConversationMessage.conversation_role_type])

            query = query.order_by(ConversationMessage.id).all()

            return [
                ConversationMessageModel.from_database_model(c) for c in query.limit(top_k)
            ]

    def _get_nearest_neighbors(self, session, query, embedding, top_k=5):
        return session.scalars(
            query.order_by(ConversationMessage.embedding.l2_distance(embedding)).limit(top_k)
        )

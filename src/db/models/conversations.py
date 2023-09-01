from typing import Union, List, Any
from uuid import UUID
from sqlalchemy.orm.attributes import InstrumentedAttribute

import openai

from sqlalchemy import select

# For testing
# Add the root path to the python path so we can import the database
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from db.database.models import User, Conversation
from db.models.vector_database import VectorDatabase, SearchType


class Conversations(VectorDatabase):
    def __init__(self, db_env_location):
        super().__init__(db_env_location)

    def store_conversation(
        self,
        session,
        conversation_text: str,
        interaction_id: UUID,
        conversation_role_type_id: int,
        user_id: Union[int, None] = None,
        additional_metadata: Union[str, None] = None,
        exception=None,
    ):
        conversation_text = conversation_text.strip()

        if len(conversation_text) == 0:
            return

        embedding = self.get_embedding(conversation_text)
        conversation = Conversation(
            interaction_id=interaction_id,
            conversation_text=conversation_text,
            user_id=user_id,
            conversation_role_type_id=conversation_role_type_id,
            additional_metadata=additional_metadata,
            embedding=embedding,
            exception=exception,
        )

        session.add(conversation)

    def search_conversations(
        self,
        session,
        conversation_text_search_query: str,
        search_type: SearchType,
        associated_user: Union[User, None] = None,
        interaction_id: Union[UUID, None] = None,
        eager_load: List[InstrumentedAttribute[Any]] = [],
        top_k=10,
        return_deleted=False,
    ) -> List[Conversation]:
        # TODO: Handle searching metadata... e.g. metadata_search_query: Union[str,None] = None

        # Can't perform this query before the
        # Before searching, pre-filter the query to only include conversations that match the single inputs
        query = session.query(Conversation).filter(
            Conversation.is_deleted == return_deleted,
            Conversation.user_id == associated_user.id
            if associated_user is not None
            else True,
            Conversation.interaction_id == interaction_id
            if interaction_id is not None
            else True,
        )

        query = super().eager_load(query, eager_load)

        if search_type == SearchType.key_word:
            # TODO: Do better key word search
            query = query.filter(
                Conversation.conversation_text.contains(conversation_text_search_query)
            )
        elif search_type == SearchType.similarity:
            embedding = self.get_embedding(conversation_text_search_query)
            query = self._get_nearest_neighbors(session, query, embedding, top_k=top_k)
        else:
            raise ValueError(f"Unknown search type: {search_type}")

        return query.all()[:top_k]

    def get_conversations_for_interaction(
        self, session, interaction_id: UUID
    ) -> List[Conversation]:
        query = session.query(Conversation).filter(
            Conversation.interaction_id == interaction_id
        ).order_by(Conversation.record_created)

        query = super().eager_load(query, [Conversation.conversation_role_type])

        return query.all()

    def get_conversations_for_user(
        self, session, user_id: int
    ) -> List[Conversation]:
        query = session.query(Conversation).filter(
            Conversation.user_id == user_id
        )

        query = super().eager_load(query, [Conversation.conversation_role_type])

        return query.order_by(Conversation.record_created).all()
    
    def update_conversation(self, session, conversation: Conversation):
        session.merge(conversation)

    def delete_conversation(self, session, conversation: Conversation):
        conversation.is_deleted = True
        session.merge(conversation)

    def _get_nearest_neighbors(self, session, query, embedding, top_k=5):
        return session.scalars(
            query.order_by(Conversation.embedding.l2_distance(embedding)).limit(top_k)
        )

if __name__ == "__main__":
    from uuid import uuid4
    from db.models.users import Users

    db_env = "src/db/database/db.env"

    conversations = Conversations(db_env)
    users = Users(db_env)

    with conversations.session_context(conversations.Session()) as session:
        # new uuid
        interaction_id = uuid4()
        messages = conversations.get_conversations_for_interaction(
            session, interaction_id
        )

        aron = users.get_user_by_email(session, "aronweiler@gmail.com")
        results = conversations.search_conversations(
            session,
            conversation_text_search_query="favorite food is",
            search_type=SearchType.similarity,
            top_k=100,
            associated_user=aron,
        )

        for result in results:
            print(result.conversation_text)

        print("---------------------------")

        results = conversations.search_conversations(
            session,
            conversation_text_search_query="food",
            search_type=SearchType.key_word,
            top_k=90,
            associated_user=aron,
        )

        for result in results:
            print(result.conversation_text)

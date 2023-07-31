from typing import Union, List, Any
from uuid import UUID
from sqlalchemy.orm.attributes import InstrumentedAttribute

import openai

from sqlalchemy import select

# For testing
# Add the root path to the python path so we can import the database
# import sys
# import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from memory.database.models import User, Conversation
from memory.models.vector_database import VectorDatabase, SearchType


class Conversations(VectorDatabase):
    def __init__(self, db_env_location):
        super().__init__(db_env_location)

    def store_conversation(
        self,
        session,
        conversation_text: str,
        interaction_id: UUID,
        associated_user: Union[User, None] = None,
        is_ai_response: bool = False,
        additional_metadata: Union[str, None] = None,
        exception = None
    ):
        if associated_user is not None:
            user_id = associated_user.id
        else:
            user_id = None

        conversation_text = conversation_text.strip()

        if len(conversation_text) == 0:
            return

        embedding = self._get_embedding(conversation_text)
        conversation = Conversation(
            interaction_id=interaction_id,
            conversation_text=conversation_text,
            user_id=user_id,
            is_ai_response=is_ai_response,
            additional_metadata=additional_metadata,
            embedding=embedding,
            exception=exception
        )

        session.add(conversation)

    def find_conversations(
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
        # Before searching, pre-filter the query to only include memories that match the single inputs
        query = session.query(Conversation).filter(
            Conversation.is_deleted == return_deleted,
            Conversation.user_id == associated_user.id
            if associated_user is not None
            else True,
            Conversation.interaction_id == interaction_id
            if interaction_id is not None
            else True,
        )

        if search_type == SearchType.key_word:
            # TODO: Do better key word search
            query = query.filter(                
                Conversation.conversation_text.contains(conversation_text_search_query)
            )
        elif search_type == SearchType.similarity:
            embedding = self._get_embedding(conversation_text_search_query)
            query = self._get_nearest_neighbors(session, query, embedding, top_k=top_k)
        else:
            raise ValueError(f"Unknown search type: {search_type}")

        query = super().eager_load(query, eager_load)

        return query.all()[:top_k]

    def get_conversations_for_interaction(
        self, session, interaction_id: UUID
    ) -> List[Conversation]:
        query = session.query(Conversation).filter(
            Conversation.interaction_id == interaction_id
        )

        return query.all()

    def update_conversation(self, session, conversation: Conversation):
        session.merge(conversation)

    def delete_conversation(self, session, conversation: Conversation):
        conversation.is_deleted = True
        session.merge(conversation)
    
    def _get_nearest_neighbors(self, session, query, embedding, top_k=5):
        return session.scalars(query.order_by(Conversation.embedding.l2_distance(embedding)).limit(top_k))        

    def _get_embedding(self, text: str, embedding_model="text-embedding-ada-002"):
        return openai.Embedding.create(input=[text], model=embedding_model)["data"][0][
            "embedding"
        ]

if __name__ == "__main__":    

    from memory.models.users import Users
    db_env = "src/memory/long_term/db.env"

    conversations = Conversations(db_env)
    users = Users(db_env)

    with conversations.session_context(conversations.Session()) as session:
        aron = users.find_user_by_email(session, "aronweiler@gmail.com")
        results = conversations.find_conversations(session, conversation_text_search_query="favorite food is", search_type=SearchType.similarity, top_k=100, associated_user=aron)

        for result in results:
            print(result.conversation_text)

        print("---------------------------")

        results = conversations.find_conversations(session, conversation_text_search_query="food", search_type=SearchType.key_word, top_k=90, associated_user=aron)

        for result in results:
            print(result.conversation_text)
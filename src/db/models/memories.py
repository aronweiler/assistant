import logging
from typing import Union, List, Any
from sqlalchemy.orm.attributes import InstrumentedAttribute

import openai

from uuid import UUID

from sqlalchemy import select

# For testing
# Add the root path to the python path so we can import the database
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))


from db.models.users import Users
from db.models.vector_database import SearchType, VectorDatabase
from db.database.models import Memory


class Memories(VectorDatabase):
    def __init__(self, db_env_location):        
        super().__init__(db_env_location)

        self.users = Users(db_env_location)

    def store_text_memory(
        self,
        session,
        memory_text: str,
        associated_user_email: Union[str, None] = None,
        interaction_id: Union[UUID, None] = None,
        additional_metadata: Union[str, None] = None,
    ):
        # look up the user and get their ID
        user = self.users.find_user_by_email(session, associated_user_email, eager_load=[])
        if user is not None:
            user_id = user.id
        else:
            user_id = None

        embedding = self._get_embedding(memory_text)
        memory = Memory(
            memory_text=memory_text,
            user_id=user_id,
            interaction_id=interaction_id,
            additional_metadata=additional_metadata,
            embedding=embedding,
        )

        session.add(memory)

    def find_memories(
        self,
        session,
        memory_text_search_query: str,
        search_type: SearchType,
        associated_user_email = None,
        interaction_id: Union[UUID, None] = None,
        eager_load: List[InstrumentedAttribute[Any]] = [],
        top_k=10,
        distance=0.5,
        return_deleted=False,
    ) -> List[Memory]:
        # TODO: Handle searching metadata... e.g. metadata_search_query: Union[str,None] = None

        # look up the user and get their ID
        user = self.users.find_user_by_email(session, associated_user_email, eager_load=[])

        # Before searching, pre-filter the query to only include memories that match the single inputs
        query = session.query(Memory).filter(
            Memory.is_deleted == return_deleted,
            Memory.user_id == user.id
            if user is not None
            else True,
            Memory.interaction_id == interaction_id
            if interaction_id is not None
            else True,
        )

        query = super().eager_load(query, eager_load)

        if search_type == SearchType.key_word:
            # TODO: Do better key word search
            query = query.filter(                
                Memory.memory_text.contains(memory_text_search_query)
            )
        elif search_type == SearchType.similarity or search_type == SearchType.key_word:
            embedding = self._get_embedding(memory_text_search_query)
            query = self._get_nearest_neighbors(session, query, embedding, top_k=top_k, distance=distance)
        else:
            raise ValueError(f"Unknown search type: {search_type}")        

        return query.all()[:top_k]

    def get_memories_for_interaction(self, session, interaction_id: UUID) -> List[Memory]:
        query = session.query(Memory).filter(Memory.interaction_id == interaction_id)

        return query.all()

    def update_memory(self, session, memory: Memory):
        session.merge(memory)

    def delete_memory(self, session, memory: Memory):
        memory.is_deleted = True
        session.merge(memory)

    def _get_nearest_neighbors(self, session, query, embedding, top_k=5, distance=0.5):
        #print("DISTANCE: ", session.scalars(select(Memory.embedding.l2_distance(embedding))))
        return session.scalars(query.order_by(Memory.embedding.l2_distance(embedding) < distance).limit(top_k))

    def _get_embedding(self, text: str, embedding_model="text-embedding-ada-002"):
        return openai.Embedding.create(input=[text], model=embedding_model)["data"][0][
            "embedding"
        ]

if __name__ == "__main__":    

    
    db_env = "src/memory/long_term/db.env"

    memories = Memories(db_env)
    users = Users(db_env)

    with memories.session_context(memories.Session()) as session:
        aron = users.find_user_by_email(session, "aronweiler@gmail.com")
        results = memories.find_memories(session, memory_text_search_query="favorite food is", search_type=SearchType.similarity, top_k=100, associated_user=aron)

        for result in results:
            print(f"User: {result.user.name} - {result.memory_text}")

        print("---------------------------")

        results = memories.find_memories(session, memory_text_search_query="food", search_type=SearchType.key_word, top_k=90, eager_load=[Memory.user])        

        for result in results:
            print(f"User: {result.user.name} - {result.memory_text}")
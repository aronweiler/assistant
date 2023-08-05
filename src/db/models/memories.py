# import logging
# from typing import Union, List, Any
# from sqlalchemy.orm.attributes import InstrumentedAttribute

# import openai

# from uuid import UUID

# from sqlalchemy import select

# # For testing
# # Add the root path to the python path so we can import the database
# import sys
# import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))


# from db.models.users import Users
# from db.models.vector_database import SearchType, VectorDatabase
# from db.database.models import Memory


# class Conversations(VectorDatabase):
#     def __init__(self, db_env_location):        
#         super().__init__(db_env_location)

#         self.users = Users(db_env_location)

#     def store_text_conversation(
#         self,
#         session,
#         conversation_text: str,
#         associated_user_email: Union[str, None] = None,
#         interaction_id: Union[UUID, None] = None,
#         additional_metadata: Union[str, None] = None,
#     ):
#         # look up the user and get their ID
#         user = self.users.find_user_by_email(session, associated_user_email, eager_load=[])
#         if user is not None:
#             user_id = user.id
#         else:
#             user_id = None

#         embedding = self._get_embedding(conversation_text)
#         conversation = Memory(
#             conversation_text=conversation_text,
#             user_id=user_id,
#             interaction_id=interaction_id,
#             additional_metadata=additional_metadata,
#             embedding=embedding,
#         )

#         session.add(conversation)

#     def search_conversations(
#         self,
#         session,
#         conversation_text_search_query: str,
#         search_type: SearchType,
#         associated_user_email = None,
#         interaction_id: Union[UUID, None] = None,
#         eager_load: List[InstrumentedAttribute[Any]] = [],
#         top_k=10,
#         distance=0.5,
#         return_deleted=False,
#     ) -> List[Memory]:
#         # TODO: Handle searching metadata... e.g. metadata_search_query: Union[str,None] = None

#         # look up the user and get their ID
#         user = self.users.find_user_by_email(session, associated_user_email, eager_load=[])

#         # Before searching, pre-filter the query to only include conversations that match the single inputs
#         query = session.query(Memory).filter(
#             Memory.is_deleted == return_deleted,
#             Memory.user_id == user.id
#             if user is not None
#             else True,
#             Memory.interaction_id == interaction_id
#             if interaction_id is not None
#             else True,
#         )

#         query = super().eager_load(query, eager_load)

#         if search_type == SearchType.key_word:
#             # TODO: Do better key word search
#             query = query.filter(                
#                 Memory.conversation_text.contains(conversation_text_search_query)
#             )
#         elif search_type == SearchType.similarity or search_type == SearchType.key_word:
#             embedding = self._get_embedding(conversation_text_search_query)
#             query = self._get_nearest_neighbors(session, query, embedding, top_k=top_k, distance=distance)
#         else:
#             raise ValueError(f"Unknown search type: {search_type}")        

#         return query.all()[:top_k]

#     def get_conversations_for_interaction(self, session, interaction_id: UUID) -> List[Memory]:
#         query = session.query(Memory).filter(Memory.interaction_id == interaction_id)

#         return query.all()

#     def update_conversation(self, session, conversation: Memory):
#         session.merge(conversation)

#     def delete_conversation(self, session, conversation: Memory):
#         conversation.is_deleted = True
#         session.merge(conversation)

#     def _get_nearest_neighbors(self, session, query, embedding, top_k=5, distance=0.5):
#         #print("DISTANCE: ", session.scalars(select(Memory.embedding.l2_distance(embedding))))
#         return session.scalars(query.order_by(Memory.embedding.l2_distance(embedding) < distance).limit(top_k))

#     def _get_embedding(self, text: str, embedding_model="text-embedding-ada-002"):
#         return openai.Embedding.create(input=[text], model=embedding_model)["data"][0][
#             "embedding"
#         ]

# if __name__ == "__main__":    

    
#     db_env = "src/db/database/db.env"

#     conversations = Conversations(db_env)
#     users = Users(db_env)

#     with conversations.session_context(conversations.Session()) as session:
#         aron = users.find_user_by_email(session, "aronweiler@gmail.com")
#         results = conversations.search_conversations(session, conversation_text_search_query="favorite food is", search_type=SearchType.similarity, top_k=100, associated_user=aron)

#         for result in results:
#             print(f"User: {result.user.name} - {result.conversation_text}")

#         print("---------------------------")

#         results = conversations.search_conversations(session, conversation_text_search_query="food", search_type=SearchType.key_word, top_k=90, eager_load=[Memory.user])        

#         for result in results:
#             print(f"User: {result.user.name} - {result.conversation_text}")
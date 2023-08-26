import json
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

from db.database.models import User, Conversation, Interaction, Document, DocumentCollection
from db.models.vector_database import VectorDatabase, SearchType


class Documents(VectorDatabase):
    def __init__(self, db_env_location):
        super().__init__(db_env_location)

    def create_collection(
        self,
        session,
        collection_name,
        interaction_id
    ):
        collection = DocumentCollection(collection_name=collection_name, interaction_id=interaction_id)        

        session.add(collection)
        return collection
    
    def get_collection(
        self,
        session,
        collection_name,
        interaction_id
    ):
        collection = session.query(DocumentCollection).filter(DocumentCollection.collection_name == collection_name).filter(DocumentCollection.interaction_id == interaction_id).first()

        return collection
        
    def get_collections(
        self,
        session,
        interaction_id
    ):
        collections = session.query(DocumentCollection).filter(DocumentCollection.interaction_id == interaction_id).all()

        return collections
    
    def get_documents(
        self,
        session,
        collection_id
    ):
        documents = session.query(Document).filter(Document.collection_id == collection_id).all()

        return documents
    
    def get_document(
        self,
        session,
        document_id
    ):
        document = session.query(Document).filter(Document.id == document_id).first()

        return document
    
    def store_document(
        self,
        session,
        collection_id,
        user_id,
        document_text,
        additional_metadata=None
    ):
        document = Document(
            collection_id=collection_id,
            user_id=user_id,
            additional_metadata=json.dumps(additional_metadata),
            document_text=document_text,
            embedding=self.get_embedding(document_text),            
        )

        session.add(document)
        return document
    
    def search_document_embeddings(
        self,
        session,
        search_query: str,
        search_type: SearchType,
        collection_id: int,
        eager_load: List[InstrumentedAttribute[Any]] = [],
        top_k=10,
    ) -> List[Conversation]:
        # # TODO: Handle searching metadata... e.g. metadata_search_query: Union[str,None] = None

        # Before searching, pre-filter the query to only include conversations that match the single inputs
        query = session.query(Document).filter(
            Document.collection_id == collection_id
        )

        query = super().eager_load(query, eager_load)

        if search_type == SearchType.key_word:
            # TODO: Do better key word search
            query = query.filter(
                Document.document_text.contains(search_query)
            )
        elif search_type == SearchType.similarity:
            embedding = self.get_embedding(search_query)
            query = self._get_nearest_neighbors(session, query, embedding, top_k=top_k)
        else:
            raise ValueError(f"Unknown search type: {search_type}")

        return query.all()[:top_k]
    
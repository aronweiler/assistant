import json
from typing import List

from pydantic import Field

from langchain.schema import BaseRetriever, BaseStore, Document
from langchain.vectorstores import VectorStore
from langchain.callbacks.manager import CallbackManagerForRetrieverRun

from db.models.documents import DocumentCollection, Documents, SearchType

class PGVectorRetriever(BaseRetriever):
    """Retrieve from a set of multiple embeddings for the same document."""

    search_kwargs: dict = {}
    vectorstore: Documents
    collection_key: str = "general"
    interaction_id: int = None
    """Keyword arguments to pass to the search function."""

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """Get documents relevant to a query.
        Args:
            query: String to find relevant documents for
            run_manager: The callbacks handler to use
        Returns:
            List of relevant documents
        """
        with self.vectorstore.session_context(self.vectorstore.Session()) as session:
            # Find the collection, first
            if 'collection_name' in self.search_kwargs:                
                collection_name = self.search_kwargs['collection_name']
            else:
                collection_name = "general"

            if 'interaction_id' in self.search_kwargs:                
                interaction_id = self.search_kwargs['interaction_id']
            else:
                interaction_id = "general"

            collection = self.vectorstore.get_collection(session, collection_name, interaction_id)

            if collection is None:
                raise ValueError(f"Collection {collection_name} does not exist for interaction {str(interaction_id)}")
            
            if 'search_type' in self.search_kwargs:                
                search_type = self.search_kwargs['search_type']
            else:
                search_type = SearchType.similarity

            if 'top_k' in self.search_kwargs:                
                top_k = self.search_kwargs['top_k']
            else:
                top_k = 4

            documents = self.vectorstore.search_document_embeddings(session, search_query=query, collection_id=collection.id, search_type=search_type, top_k=top_k)

            # Transform these into the document type expected by langchain
            documents = [
                Document(
                    page_content=document.document_text,
                    metadata=json.loads(document.additional_metadata)
                )
                for document in documents
            ]
        
        return documents

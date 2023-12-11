import json
from typing import List

from pydantic import Field

from langchain.schema import BaseRetriever, Document
from langchain.callbacks.manager import CallbackManagerForRetrieverRun

from src.db.models.documents import Documents, SearchType


class PGVectorRetriever(BaseRetriever):
    """Retrieve from a set of multiple embeddings for the same document."""

    search_kwargs: dict = {}
    """Keyword arguments to pass to the search function."""

    vectorstore: Documents

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
        # Find the collection, first
        if (
            "collection_id" in self.search_kwargs
            and self.search_kwargs["collection_id"]
        ):
            collection_id = self.search_kwargs["collection_id"]
        else:
            raise Exception("collection_id must be specified in search_kwargs")

        if (
            "conversation_id" in self.search_kwargs
            and self.search_kwargs["conversation_id"]
        ):
            conversation_id = self.search_kwargs["conversation_id"]
        else:
            raise Exception("conversation_id must be specified in search_kwargs")

        collection = self.vectorstore.get_collection(collection_id)

        if collection is None:
            raise Exception(
                f"Collection '{collection_id}' for interaction '{conversation_id}' not found"
            )

        if "search_type" in self.search_kwargs:
            search_type = self.search_kwargs["search_type"]
        else:
            search_type = SearchType.Similarity

        if "target_file_id" in self.search_kwargs:
            target_file_id = self.search_kwargs["target_file_id"]
        else:
            target_file_id = None

        if "top_k" in self.search_kwargs:
            top_k = self.search_kwargs["top_k"]
        else:
            top_k = 4

        documents = self.vectorstore.search_document_embeddings(
            search_query=query,
            collection_id=collection_id,
            search_type=search_type,
            top_k=top_k,
            target_file_id=target_file_id,
        )

        # Transform these into the document type expected by langchain
        documents_to_return = []
        for document in documents:
            page_content = document.document_text
            metadata = document.additional_metadata

            # This is where I can add any additional metadata I want to return.
            # File ID is used by the LLM for referencing files.
            metadata["file_id"] = document.file_id

            documents_to_return.append(
                Document(page_content=page_content, metadata=metadata)
            )

        return documents_to_return

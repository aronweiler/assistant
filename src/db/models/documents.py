import sys
import os

from typing import List, Any

from sqlalchemy.orm.attributes import InstrumentedAttribute

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.db.database.models import (
    Document,
    DocumentCollection,
    File,
)

from src.db.models.vector_database import VectorDatabase, SearchType
from src.db.models.domain.document_collection_model import DocumentCollectionModel
from src.db.models.domain.document_model import DocumentModel
from src.db.models.domain.file_model import FileModel


class Documents(VectorDatabase):
    def create_collection(
        self, collection_name, interaction_id
    ) -> DocumentCollectionModel:
        with self.session_context(self.Session()) as session:
            collection = DocumentCollection(
                collection_name=collection_name, interaction_id=interaction_id
            )

            session.add(collection)
            session.commit()

            return DocumentCollectionModel.from_database_model(collection)

    def get_collection(self, collection_id, interaction_id) -> DocumentCollectionModel:
        with self.session_context(self.Session()) as session:
            collection = (
                session.query(DocumentCollection)
                .filter(DocumentCollection.id == collection_id)
                .filter(DocumentCollection.interaction_id == interaction_id)
                .first()
            )

            return DocumentCollectionModel.from_database_model(collection)

    def get_collection_by_name(
        self, collection_name, interaction_id
    ) -> DocumentCollectionModel:
        with self.session_context(self.Session()) as session:
            collection = (
                session.query(DocumentCollection)
                .filter(DocumentCollection.collection_name == collection_name)
                .filter(DocumentCollection.interaction_id == interaction_id)
                .first()
            )

            return DocumentCollectionModel.from_database_model(collection)

    def get_collections(self, interaction_id) -> List[DocumentCollectionModel]:
        with self.session_context(self.Session()) as session:
            collections = (
                session.query(DocumentCollection)
                .filter(DocumentCollection.interaction_id == interaction_id)
                .all()
            )

            return [DocumentCollectionModel.from_database_model(c) for c in collections]

    def create_file(
        self,
        file: FileModel
    ) -> FileModel:
        with self.session_context(self.Session()) as session:
            file = file.to_database_model()
            session.add(file)
            session.commit()

            return FileModel.from_database_model(file)

    def update_file_summary_and_class(
        self,
        file_id: int,
        summary: str,
        classification: str,
    ) -> FileModel:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == file_id).first()
            file.file_summary = summary
            file.file_classification = classification
            session.commit()

            return FileModel.from_database_model(file)

    def get_files_in_collection(self, collection_id) -> List[FileModel]:
        with self.session_context(self.Session()) as session:
            files = (
                session.query(File)
                    .filter(File.collection_id == collection_id)
                    .all()
            )

            return [FileModel.from_database_model(f) for f in files]

    def get_file(self, file_id) -> FileModel:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == file_id).first()

            return FileModel.from_database_model(file)
        
    def get_all_files(self) -> List[FileModel]:
        with self.session_context(self.Session()) as session:
            files = session.query(File).all()

            return [FileModel.from_database_model(f) for f in files]
        
    def delete_file(self, file_id) -> None:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == file_id).first()

            session.delete(file)
            session.commit()

    def get_file_by_name(self, file_name, collection_id) -> FileModel:
        with self.session_context(self.Session()) as session:
            file = (
                session.query(File)
                .filter(File.file_name == file_name)
                .filter(File.collection_id == collection_id)
                .first()
            )

            return FileModel.from_database_model(file)

    def get_document_chunks_by_file_id(self, target_file_id) -> List[DocumentModel]:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == target_file_id).first()

            if file is None:
                raise ValueError(f"File with ID '{target_file_id}' does not exist")

            documents = (
                session.query(Document).filter(Document.file_id == file.id).all()
            )

            return [DocumentModel.from_database_model(d) for d in documents]
        
    def delete_document_chunks_by_file_id(self, target_file_id) -> None:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == target_file_id).first()

            if file is None:
                raise ValueError(f"File with ID '{target_file_id}' does not exist")

            # Find all of the documents associated with this file
            documents = (
                session.query(Document)
                .filter(Document.file_id == file.id)
                .all()
            )

            # Delete all of the documents associated with this file, and the file itself
            for document in documents:
                session.delete(document)

            session.commit()

    def get_collection_files(self, collection_id) -> List[FileModel]:
        with self.session_context(self.Session()) as session:
            files = (
                session.query(File).filter(File.collection_id == collection_id).all()
            )

            return [FileModel.from_database_model(f) for f in files]

    def store_document(self, document: DocumentModel) -> DocumentModel:
        with self.session_context(self.Session()) as session:
            embedding = self.get_embedding(document.document_text)
            document = document.to_database_model()
            document.embedding = embedding

            session.add(document)
            session.commit()

            return DocumentModel.from_database_model(document)

    def search_document_embeddings(
        self,
        search_query: str,
        search_type: SearchType,
        collection_id: int,
        target_file_id: int = None,
        eager_load: List[InstrumentedAttribute[Any]] = [],
        top_k=10,
    ) -> List[DocumentModel]:
        # # TODO: Handle searching metadata... e.g. metadata_search_query: Union[str,None] = None

        with self.session_context(self.Session()) as session:
            # Before searching, pre-filter the query to only include conversations that match the single inputs
            query = session.query(Document)

            if collection_id is not None:
                query = query.filter(Document.collection_id == collection_id)

            if target_file_id is not None:
                query = query.filter(Document.file_id == target_file_id)

            query = super().eager_load(query, eager_load)

            if search_type == SearchType.key_word:
                # TODO: Do better key word search
                query = query.filter(
                    Document.document_text.contains(search_query)
                ).limit(top_k)
            elif search_type == SearchType.similarity:
                embedding = self.get_embedding(search_query)
                query = self._get_nearest_neighbors(
                    session, query, embedding, top_k=top_k
                )
            else:
                raise ValueError(f"Unknown search type: {search_type}")

            return [DocumentModel.from_database_model(d) for d in query.all()[:top_k]]

    def _get_nearest_neighbors(self, session, query, embedding, top_k=5):
        return session.scalars(
            query.order_by(Document.embedding.l2_distance(embedding)).limit(top_k)
        )


# Testing
if __name__ == "__main__":
    document_helper = Documents()

    documents = document_helper.search_document_embeddings(
        search_query="comfort stations",
        search_type=SearchType.similarity,
        collection_id=5,
        top_k=100,
    )

    for doc in documents:
        print(doc.document_text)
        print("---------------")

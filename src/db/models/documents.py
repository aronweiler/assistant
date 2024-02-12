import sys
import os

from typing import List, Any

from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import func, select, column, cast, or_

import pgvector.sqlalchemy

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.db.database.tables import (
    Document,
    DocumentCollection,
    File,
)

from src.db.models.vector_database import VectorDatabase, SearchType
from src.db.models.domain.document_collection_model import DocumentCollectionModel
from src.db.models.domain.document_model import DocumentModel
from src.db.models.domain.file_model import FileModel

from src.ai.utilities.embeddings_helper import get_embedding_by_name, get_embedding_by_model


class Documents(VectorDatabase):
    def create_collection(
        self, collection_name, embedding_name
    ) -> DocumentCollectionModel:
        with self.session_context(self.Session()) as session:
            collection = DocumentCollection(
                collection_name=collection_name, embedding_name=embedding_name
            )

            session.add(collection)
            session.commit()

            return DocumentCollectionModel.from_database_model(collection)

    def delete_collection(self, collection_id) -> None:
        with self.session_context(self.Session()) as session:
            collection = (
                session.query(DocumentCollection)
                .filter(DocumentCollection.id == collection_id)
                .first()
            )

            session.delete(collection)
            session.commit()

    def get_collection(self, collection_id) -> DocumentCollectionModel:
        with self.session_context(self.Session()) as session:
            collection = (
                session.query(
                    DocumentCollection.id,
                    DocumentCollection.collection_name,
                    DocumentCollection.record_created,
                    DocumentCollection.embedding_name,
                )
                .filter(DocumentCollection.id == collection_id)
                .first()
            )

            return DocumentCollectionModel.from_database_model(collection)

    def get_collection_by_name(self, collection_name) -> DocumentCollectionModel:
        with self.session_context(self.Session()) as session:
            collection = (
                session.query(
                    DocumentCollection.id,
                    DocumentCollection.collection_name,
                    DocumentCollection.record_created,
                    DocumentCollection.embedding_name,
                )
                .filter(DocumentCollection.collection_name == collection_name)
                .first()
            )

            return DocumentCollectionModel.from_database_model(collection)

    def get_collections(self) -> List[DocumentCollectionModel]:
        with self.session_context(self.Session()) as session:
            collections = session.query(
                DocumentCollection.id,
                DocumentCollection.collection_name,
                DocumentCollection.record_created,
                DocumentCollection.embedding_name,
            ).all()

            return [DocumentCollectionModel.from_database_model(c) for c in collections]

    def create_file(self, file: FileModel, file_data) -> FileModel:
        with self.session_context(self.Session()) as session:
            file = file.to_database_model()
            file.file_data = file_data
            session.add(file)
            session.commit()

            return FileModel.from_database_model(file)

    def set_file_data(self, file_id: int, file_data) -> FileModel:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == file_id).first()
            file.file_data = file_data
            session.commit()

            return FileModel.from_database_model(file)

    def set_collection_id_for_file(self, file_id: int, collection_id: int) -> FileModel:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == file_id).first()
            file.collection_id = collection_id
            session.commit()

            return FileModel.from_database_model(file)

    def get_file_data(self, file_id: int) -> Any:
        with self.session_context(self.Session()) as session:
            file = (
                session.query(File.id, File.file_data)
                .filter(File.id == file_id)
                .first()
            )
            return file.file_data

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

    def get_file(self, file_id) -> FileModel:
        with self.session_context(self.Session()) as session:
            file = (
                session.query(
                    File.collection_id,
                    File.user_id,
                    File.file_name,
                    File.file_hash,
                    File.chunk_size,
                    File.chunk_overlap,
                    File.document_count,
                    File.id,
                    File.file_classification,
                    File.file_summary,
                    File.record_created,
                )
                .filter(File.id == file_id)
                .first()
            )

            return FileModel.from_database_model(file)

    def get_all_files(self) -> List[FileModel]:
        with self.session_context(self.Session()) as session:
            files = session.query(
                File.collection_id,
                File.user_id,
                File.file_name,
                File.file_hash,
                File.chunk_size,
                File.chunk_overlap,
                File.document_count,
                File.id,
                File.file_classification,
                File.file_summary,
                File.record_created,
            ).all()

            return [FileModel.from_database_model(f) for f in files]

    def get_files_in_collection(self, collection_id) -> List[FileModel]:
        with self.session_context(self.Session()) as session:
            files = (
                session.query(
                    File.collection_id,
                    File.user_id,
                    File.file_name,
                    File.file_hash,
                    File.chunk_size,
                    File.chunk_overlap,
                    File.document_count,
                    File.id,
                    File.file_classification,
                    File.file_summary,
                    File.record_created,
                )
                .filter(File.collection_id == collection_id)
                .all()
            )

            return [FileModel.from_database_model(f) for f in files]

    def delete_file(self, file_id) -> None:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == file_id).first()

            session.delete(file)
            session.commit()

    def get_file_by_name(self, file_name, collection_id) -> FileModel:
        with self.session_context(self.Session()) as session:
            file = (
                session.query(
                    File.collection_id,
                    File.user_id,
                    File.file_name,
                    File.file_hash,
                    File.chunk_size,
                    File.chunk_overlap,
                    File.document_count,
                    File.id,
                    File.file_classification,
                    File.file_summary,
                    File.record_created,
                )
                .filter(File.file_name == file_name)
                .filter(File.collection_id == collection_id)
                .first()
            )

            return FileModel.from_database_model(file)

    def get_document_chunk_count_by_file_id(self, target_file_id) -> int:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == target_file_id).first()

            if file is None:
                raise ValueError(f"File with ID '{target_file_id}' does not exist")

            return session.query(Document).filter(Document.file_id == file.id).count()

    def get_document_chunks_by_file_id(self, target_file_id) -> List[DocumentModel]:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == target_file_id).first()

            if file is None:
                raise ValueError(f"File with ID '{target_file_id}' does not exist")

            documents = (
                session.query(
                    Document.collection_id,
                    Document.file_id,
                    Document.user_id,
                    Document.document_text,
                    Document.document_name,
                    Document.document_text_summary,
                    Document.document_text_has_summary,
                    Document.id,
                    Document.additional_metadata,
                    Document.record_created,
                    Document.embedding_model_name,
                    Document.question_1,
                    Document.question_2,
                    Document.question_3,
                    Document.question_4,
                    Document.question_5,
                )
                .filter(Document.file_id == file.id)
                .all()
            )

            return [DocumentModel.from_database_model(d) for d in documents]

    def set_collection_id_for_document_chunks(
        self, file_id: int, collection_id: int
    ) -> None:
        with self.session_context(self.Session()) as session:
            documents = (
                session.query(Document).filter(Document.file_id == file_id).all()
            )

            for document in documents:
                document.collection_id = collection_id

            session.commit()

    def get_document_summaries(self, target_file_id) -> List[str]:
        with self.session_context(self.Session()) as session:
            file = session.query(File.id).filter(File.id == target_file_id).first()

            if file is None:
                raise ValueError(f"File with ID '{target_file_id}' does not exist")

            documents = (
                session.query(
                    Document.collection_id,
                    Document.file_id,
                    Document.document_text_summary,
                    Document.document_text_has_summary,
                    Document.record_created,
                )
                .filter(
                    Document.file_id == file.id,
                    Document.document_text_has_summary == True,
                )
                .all()
            )

            return [d.document_text_summary for d in documents]

    def delete_document_chunks_by_file_id(self, target_file_id) -> None:
        with self.session_context(self.Session()) as session:
            file = session.query(File.id).filter(File.id == target_file_id).first()

            if file is None:
                raise ValueError(f"File with ID '{target_file_id}' does not exist")

            # Find all of the documents associated with this file
            documents = (
                session.query(Document).filter(Document.file_id == file.id).all()
            )

            # Delete all of the documents associated with this file, and the file itself
            for document in documents:
                session.delete(document)

            session.commit()

    def update_document_count(self, file_id: int, document_chunk_count: int) -> None:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == file_id).first()
            file.document_count = document_chunk_count
            session.commit()

    def store_document(self, document: DocumentModel) -> DocumentModel:
        with self.session_context(self.Session()) as session:
            # Generate the embedding for the document text
            embedding = get_embedding_by_model(
                text=document.document_text,
                model_name=document.embedding_model_name,
                instruction="Represent the document for retrieval: ",
            )

            # Generate the embedding for the document text summary
            document_text_summary_embedding = None
            if document.document_text_summary.strip() != "":
                document_text_summary_embedding = get_embedding_by_model(
                    document.document_text_summary,
                    model_name=document.embedding_model_name,
                    instruction="Represent the summary for retrieval: ",
                )

            # Generate the embeddings for the questions
            question_embeddings = []
            for question_number in range(1, 6):
                question = getattr(document, f"question_{question_number}")
                if str(question).strip() != "":
                    question_embedding = get_embedding_by_model(
                        question,
                        model_name=document.embedding_model_name,
                        instruction=f"Represent the question for retrieval: ",
                    )
                    question_embeddings.append(question_embedding)
                else:
                    question_embeddings.append(None)

            document = document.to_database_model()
            document.embedding = embedding
            document.document_text_summary_embedding = document_text_summary_embedding
            document.embedding_question_1 = (
                question_embeddings[0] if question_embeddings[0] is not None else None
            )
            document.embedding_question_2 = (
                question_embeddings[1] if question_embeddings[1] is not None else None
            )
            document.embedding_question_3 = (
                question_embeddings[2] if question_embeddings[2] is not None else None
            )
            document.embedding_question_4 = (
                question_embeddings[3] if question_embeddings[3] is not None else None
            )
            document.embedding_question_5 = (
                question_embeddings[4] if question_embeddings[4] is not None else None
            )

            session.add(document)
            session.commit()

            return DocumentModel.from_database_model(document)

    def set_document_text_summary(
        self, document_id: int, document_text_summary: str, collection_id: int
    ):
        embedding_name = self.get_collection(
            collection_id=collection_id
        ).embedding_name

        with self.session_context(self.Session()) as session:
            document_text_summary_embedding = None
            if document_text_summary.strip() != "":
                document_text_summary_embedding = get_embedding_by_name(
                    document_text_summary,
                    embedding_name=embedding_name,
                    instruction="Represent the summary for retrieval: ",
                )

                session.query(Document).filter(Document.id == document_id).update(
                    {
                        Document.document_text_summary: document_text_summary,
                        Document.document_text_summary_embedding: document_text_summary_embedding,
                        Document.document_text_has_summary: True,
                    }
                )

                session.commit()

    def search_document_embeddings(
        self,
        search_query: str,
        search_type: SearchType,
        collection_id: int,
        target_file_id: int = None,
        top_k=10,
        search_questions: bool = True,
    ) -> List[DocumentModel]:
        # # TODO: Handle searching metadata... e.g. metadata_search_query: Union[str,None] = None

        embedding_name = self.get_collection(
            collection_id=collection_id
        ).embedding_name

        with self.session_context(self.Session()) as session:
            # Before searching, pre-filter the query to only include conversations that match the single inputs
            query = session.query(
                Document.collection_id,
                Document.file_id,
                Document.user_id,
                Document.document_text,
                Document.document_name,
                Document.document_text_summary,
                Document.document_text_has_summary,
                Document.id,
                Document.additional_metadata,
                Document.record_created,
                Document.embedding_model_name,
                Document.question_1,
                Document.question_2,
                Document.question_3,
                Document.question_4,
                Document.question_5,
            )

            if collection_id is not None:
                query = query.filter(Document.collection_id == collection_id)

            if target_file_id is not None:
                query = query.filter(Document.file_id == target_file_id)

            if type(search_type) == str:
                search_type = SearchType(search_type)

            if search_type == SearchType.Keyword:
                # TODO: Do better key word search

                if type(search_query) == str:
                    search_query = [search_query]

                query = query.filter(
                    or_(
                        func.lower(Document.document_text).contains(func.lower(kword))
                        for kword in search_query
                    )
                )

                return [
                    DocumentModel.from_database_model(d) for d in query.all()[:top_k]
                ]

            elif search_type == SearchType.Similarity:
                query_embedding = get_embedding_by_name(
                    text=search_query,
                    embedding_name=embedding_name,
                    instruction="Represent the query for retrieval: ",
                )

                embedding_results = []

                embedding_results.append(
                    self._get_nearest_neighbors(
                        session=session,
                        collection_id=collection_id,
                        target_file_id=target_file_id,
                        embedding_prop=Document.embedding,
                        embedding=query_embedding,
                        top_k=top_k,
                    )
                )

                embedding_results.append(
                    self._get_nearest_neighbors(
                        session=session,
                        collection_id=collection_id,
                        target_file_id=target_file_id,
                        embedding_prop=Document.document_text_summary_embedding,
                        embedding=query_embedding,
                        top_k=top_k,
                    )
                )

                if search_questions:
                    # Search each of the generated question embeddings
                    for question_number in range(1, 6):
                        embedding_results.append(
                            self._get_nearest_neighbors(
                                session=session,
                                collection_id=collection_id,
                                target_file_id=target_file_id,
                                embedding_prop=getattr(
                                    Document, f"embedding_question_{question_number}"
                                ),
                                embedding=query_embedding,
                                top_k=top_k,
                            )
                        )

                results = self._combine_document_embedding_queries(
                    embedding_results=embedding_results,
                    top_k=top_k,
                )

                # TODO: Add an arg to allow passing back the distance, as well.
                return [doc["document"] for doc in results]

            else:
                raise ValueError(f"Unknown search type: {search_type}")

    def _combine_document_embedding_queries(
        self, embedding_results: list, top_k
    ) -> str:
        def reorder_dict_by_distance(dict_list):
            # Remove anything that doesn't have a distance (e.g. probably didn't have a summary)
            filtered_list = [
                item for item in dict_list if item.get("distance") is not None
            ]

            sorted_dict_list = sorted(filtered_list, key=lambda x: x["distance"])

            return sorted_dict_list

        # Convert the results into a list of dictionaries
        new_embedding_results = []
        for embeddings in embedding_results:
            for d in embeddings:
                new_embedding_results.append(
                    {
                        "document": DocumentModel.from_database_model(d[0]),
                        "distance": d[1],
                        "l2_distance": d[2],
                    }
                )

        # Now we need to take these two dictionaries, sort them by distance, and then combine them while removing duplicates
        def combine_and_remove_duplicates(list_of_dictionaries):
            # Combine the two lists and reorder by distance
            combined_list = reorder_dict_by_distance(list_of_dictionaries)

            unique_documents = {}
            unique_list = []

            for item in combined_list:
                document_id = item["document"].id

                # Check if the document ID is not already in the dictionary
                if document_id not in unique_documents:
                    # Mark as seen
                    unique_documents[document_id] = True
                    # Add the dictionary to the unique list
                    unique_list.append(item)

            return unique_list

        combined_list = combine_and_remove_duplicates(new_embedding_results)

        # Re-rank the list using a re-ranking function
        # TODO: Add a re-ranking function

        # Now the list contains a sorted and de-duped combination of the two lists, but it may be longer than the top_k
        # Return the list limited to the original top_k
        return combined_list[:top_k]

    def _get_nearest_neighbors(
        self,
        session,
        collection_id: int,
        embedding_prop,
        embedding,
        target_file_id: int = None,
        top_k=5,
    ):
        emb_val = cast(embedding, pgvector.sqlalchemy.Vector)
        cosine_distance = func.cosine_distance(embedding_prop, emb_val)
        l2_distance = func.l2_distance(embedding_prop, emb_val)

        statement = (
            select(Document)
            .filter(
                Document.collection_id == collection_id,
                Document.file_id == target_file_id if target_file_id else True,
            )
            .order_by(cosine_distance)
            .limit(top_k)
            .add_columns(cosine_distance)
            .add_columns(l2_distance)
        )
        result = session.execute(statement)

        return result


# Testing
if __name__ == "__main__":
    document_helper = Documents()

    # similarity_documents = document_helper.search_document_embeddings(
    #     search_query="hello",
    #     search_type=SearchType.Similarity,
    #     collection_id=6,
    #     top_k=5,
    # )

    # for doc in similarity_documents:
    #     print(f"Chunk: {doc.id}, Doc: {doc.document_name}")
    #     print("---------------")

    keyword_documents = document_helper.search_document_embeddings(
        search_query=["Truvian", "Becton Dickinson", "Aron"],
        search_type=SearchType.Keyword,
        collection_id=2,
        top_k=5,
    )

    for doc in keyword_documents:
        print(f"KEYWORD: Chunk: {doc.id}, Doc: {doc.document_name}")
        print("---------------")

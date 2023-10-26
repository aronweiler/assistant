import sys
import os

from typing import List, Any

from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import func, select, column, cast, or_

import pgvector.sqlalchemy

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.db.database.models import (
    Document,
    DocumentCollection,
    File,
)

from src.db.database.models import EMBEDDING_DIMENSIONS
from src.db.models.vector_database import VectorDatabase, SearchType
from src.db.models.domain.document_collection_model import DocumentCollectionModel
from src.db.models.domain.document_model import DocumentModel
from src.db.models.domain.file_model import FileModel


class Documents(VectorDatabase):
    def create_collection(self, collection_name) -> DocumentCollectionModel:
        with self.session_context(self.Session()) as session:
            collection = DocumentCollection(collection_name=collection_name)

            session.add(collection)
            session.commit()

            return DocumentCollectionModel.from_database_model(collection)

    def get_collection(self, collection_id) -> DocumentCollectionModel:
        with self.session_context(self.Session()) as session:
            collection = (
                session.query(DocumentCollection)
                .filter(DocumentCollection.id == collection_id)
                .first()
            )

            return DocumentCollectionModel.from_database_model(collection)

    def get_collection_by_name(self, collection_name) -> DocumentCollectionModel:
        with self.session_context(self.Session()) as session:
            collection = (
                session.query(DocumentCollection)
                .filter(DocumentCollection.collection_name == collection_name)
                .first()
            )

            return DocumentCollectionModel.from_database_model(collection)

    def get_collections(self) -> List[DocumentCollectionModel]:
        with self.session_context(self.Session()) as session:
            collections = session.query(DocumentCollection.id, DocumentCollection.collection_name, DocumentCollection.record_created).all()

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
        
    def get_file_data(self, file_id: int) -> Any:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == file_id).first()
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

    def get_files_in_collection(self, collection_id) -> List[FileModel]:
        with self.session_context(self.Session()) as session:
            files = (
                session.query(File).filter(File.collection_id == collection_id).all()
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
        
    def get_document_summaries(self, target_file_id) -> List[str]:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == target_file_id).first()

            if file is None:
                raise ValueError(f"File with ID '{target_file_id}' does not exist")

            documents = (
                session.query(Document).filter(Document.file_id == file.id).all()
            )

            return [d.document_text_summary for d in documents]

    def delete_document_chunks_by_file_id(self, target_file_id) -> None:
        with self.session_context(self.Session()) as session:
            file = session.query(File).filter(File.id == target_file_id).first()

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

    def get_collection_files(self, collection_id) -> List[FileModel]:
        with self.session_context(self.Session()) as session:
            files = (
                session.query(File).filter(File.collection_id == collection_id).all()
            )

            return [FileModel.from_database_model(f) for f in files]

    def store_document(self, document: DocumentModel) -> DocumentModel:
        with self.session_context(self.Session()) as session:
            embedding = self.get_embedding(document.document_text)
            document_text_summary_embedding = None
            if document.document_text_summary.strip() != "":
                document_text_summary_embedding = self.get_embedding(
                    document.document_text_summary
                )
            document = document.to_database_model()
            document.embedding = embedding
            document.document_text_summary_embedding = document_text_summary_embedding

            session.add(document)
            session.commit()

            return DocumentModel.from_database_model(document)

    def set_document_text_summary(self, document_id: int, document_text_summary):
        with self.session_context(self.Session()) as session:
            document_text_summary_embedding = None
            if document_text_summary.strip() != "":
                document_text_summary_embedding = self.get_embedding(
                    document_text_summary
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
    ) -> List[DocumentModel]:
        # # TODO: Handle searching metadata... e.g. metadata_search_query: Union[str,None] = None

        with self.session_context(self.Session()) as session:
            # Before searching, pre-filter the query to only include conversations that match the single inputs
            query = session.query(Document)

            if collection_id is not None:
                query = query.filter(Document.collection_id == collection_id)

            if target_file_id is not None:
                query = query.filter(Document.file_id == target_file_id)

            if type(search_type) == str:
                search_type = SearchType(search_type)

            if search_type == SearchType.Keyword:
                # TODO: Do better key word search
                #select(sometable.c.text.match("search string"))
                #val = select(Document.id).where(Document.document_text.match(search_query))
                #query = query.filter(func.lower(Document.document_text).contains(func.lower(search_query)))
                
                if type(search_query) == str:
                    search_query = [search_query]             
                       
                query = query.filter(or_(func.lower(Document.document_text).contains(func.lower(kword)) for kword in search_query))
                #query = query.filter(func.lower(Document.document_text).contains(func.lower(keyword)) | func.lower(Document.document_text_summary).contains(func.lower(keyword)))
                
                # query = query.filter(
                #     Document.document_text.ilike(search_query) # Would rather use this, but can't get it working atm
                # ).limit(top_k)
                
                # for row in session.execute(val):
                #     print(row)

                return [
                    DocumentModel.from_database_model(d) for d in query.all()[:top_k]
                ]

            elif search_type == SearchType.Similarity:
                query_embedding = self.get_embedding(search_query)

                document_text_embedding_results = self._get_nearest_neighbors(
                    session=session,
                    collection_id=collection_id,
                    target_file_id=target_file_id,
                    embedding_prop=Document.embedding,
                    embedding=query_embedding,
                    top_k=top_k,
                )

                document_text_summary_embedding_results = self._get_nearest_neighbors(
                    session=session,
                    collection_id=collection_id,
                    target_file_id=target_file_id,
                    embedding_prop=Document.document_text_summary_embedding,
                    embedding=query_embedding,
                    top_k=top_k,
                )

                results = self._combine_document_text_embedding_queries(
                    text_embedding_results=document_text_embedding_results,
                    text_summary_embedding_results=document_text_summary_embedding_results,
                    top_k=top_k,
                )

                # TODO: Add an arg to allow passing back the distance, as well.
                return [doc["document"] for doc in results]

            else:
                raise ValueError(f"Unknown search type: {search_type}")

    def _combine_document_text_embedding_queries(
        self, text_embedding_results, text_summary_embedding_results, top_k
    ) -> str:
        def reorder_dict_by_distance(dict_list):
            # Remove anything that doesn't have a distance (e.g. probably didn't have a summary)
            filtered_list = [
                item for item in dict_list if item.get("distance") is not None
            ]

            sorted_dict_list = sorted(filtered_list, key=lambda x: x["distance"])

            return sorted_dict_list

        text_embeddings_dict = [
            {"document": DocumentModel.from_database_model(d[0]), "distance": d[1], "l2_distance": d[2]}
            for d in text_embedding_results
        ]
        text_summary_embeddings_dict = [
            {"document": DocumentModel.from_database_model(d[0]), "distance": d[1], "l2_distance": d[2]}
            for d in text_summary_embedding_results
        ]

        # Now we need to take these two dictionaries, sort them by distance, and then combine them while removing duplicates
        def combine_and_remove_duplicates(list1, list2):
            # Combine the two lists and reorder by distance
            combined_list = reorder_dict_by_distance(list1 + list2)

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

        combined_list = combine_and_remove_duplicates(
            text_embeddings_dict, text_summary_embeddings_dict
        )

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
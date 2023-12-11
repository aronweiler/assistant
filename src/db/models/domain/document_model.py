import json

from src.db.database.tables import Document


class DocumentModel:
    def __init__(
        self,
        collection_id,
        file_id,
        user_id,
        document_text,
        document_name,
        document_text_summary,
        document_text_has_summary,
        embedding_model_name,        
        id=None,
        additional_metadata: dict = {},
        record_created=None,
        question_1:str = None,
        question_2:str = None,
        question_3:str = None,
        question_4:str = None,
        question_5:str = None,
    ):
        self.id = id
        self.collection_id = collection_id
        self.file_id = file_id
        self.user_id = user_id
        self.additional_metadata = additional_metadata
        self.document_text = document_text
        self.document_name = document_name
        self.document_text_summary = document_text_summary
        self.document_text_has_summary = document_text_has_summary
        self.record_created = record_created
        self.embedding_model_name = embedding_model_name
        self.question_1 = question_1
        self.question_2 = question_2
        self.question_3 = question_3
        self.question_4 = question_4
        self.question_5 = question_5

    def to_database_model(self):
        return Document(
            id=self.id,
            collection_id=self.collection_id,
            file_id=self.file_id,
            user_id=self.user_id,
            additional_metadata=json.dumps(self.additional_metadata),
            document_text=self.document_text,
            document_name=self.document_name,
            document_text_summary=self.document_text_summary,
            document_text_has_summary=self.document_text_has_summary,
            record_created=self.record_created,
            embedding_model_name=self.embedding_model_name,
            question_1=self.question_1,
            question_2=self.question_2,
            question_3=self.question_3,
            question_4=self.question_4,
            question_5=self.question_5,
        )

    @classmethod
    def from_database_model(cls, db_document):
        if not db_document:
            return None
        
        return cls(
            id=db_document.id,
            collection_id=db_document.collection_id,
            file_id=db_document.file_id,
            user_id=db_document.user_id,
            additional_metadata=json.loads(db_document.additional_metadata),
            document_text=db_document.document_text,
            document_name=db_document.document_name,
            document_text_summary=db_document.document_text_summary,
            document_text_has_summary=db_document.document_text_has_summary,
            record_created=db_document.record_created,
            embedding_model_name=db_document.embedding_model_name,
            question_1=db_document.question_1,
            question_2=db_document.question_2,
            question_3=db_document.question_3,
            question_4=db_document.question_4,
            question_5=db_document.question_5,
        )

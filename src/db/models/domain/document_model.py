import json

from src.db.database.models import Document


class DocumentModel:
    def __init__(
        self,
        collection_id,
        file_id,
        user_id,
        document_text,
        document_name,
        id=None,
        additional_metadata: dict = {},
        record_created=None,
    ):
        self.id = id
        self.collection_id = collection_id
        self.file_id = file_id
        self.user_id = user_id
        self.additional_metadata = additional_metadata
        self.document_text = document_text
        self.document_name = document_name
        self.record_created = record_created

    def to_database_model(self):
        return Document(
            id=self.id,
            collection_id=self.collection_id,
            file_id=self.file_id,
            user_id=self.user_id,
            additional_metadata=json.dumps(self.additional_metadata),
            document_text=self.document_text,
            document_name=self.document_name,
            record_created=self.record_created,
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
            record_created=db_document.record_created
        )

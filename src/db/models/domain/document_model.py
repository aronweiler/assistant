from db.database.models import Document

class DocumentModel:
    def __init__(self, id, collection_id, file_id, user_id, additional_metadata, document_text,
                 document_name, embedding, record_created, user=None, collection=None, file=None):
        self.id = id
        self.collection_id = collection_id
        self.file_id = file_id
        self.user_id = user_id
        self.additional_metadata = additional_metadata
        self.document_text = document_text
        self.document_name = document_name
        self.embedding = embedding
        self.record_created = record_created
        self.user = user
        self.collection = collection
        self.file = file

    def to_database_model(self):
        return Document(
            id=self.id,
            collection_id=self.collection_id,
            file_id=self.file_id,
            user_id=self.user_id,
            additional_metadata=self.additional_metadata,
            document_text=self.document_text,
            document_name=self.document_name,
            embedding=self.embedding,
            record_created=self.record_created,
            user=self.user,
            collection=self.collection,
            file=self.file
        )

    @classmethod
    def from_database_model(cls, db_document):
        return cls(
            id=db_document.id,
            collection_id=db_document.collection_id,
            file_id=db_document.file_id,
            user_id=db_document.user_id,
            additional_metadata=db_document.additional_metadata,
            document_text=db_document.document_text,
            document_name=db_document.document_name,
            embedding=db_document.embedding,
            record_created=db_document.record_created,
            user=db_document.user,
            collection=db_document.collection,
            file=db_document.file
        )

from src.db.database.models import DocumentCollection

class DocumentCollectionModel:
    def __init__(self, id, collection_name, record_created=None, documents=None, files=None):
        self.id = id
        self.collection_name = collection_name
        self.record_created = record_created
        self.documents = documents or []
        self.files = files or []

    def to_database_model(self):
        return DocumentCollection(
            id=self.id,
            collection_name=self.collection_name,
            record_created=self.record_created,
            documents=self.documents,
            files=self.files
        )

    @classmethod
    def from_database_model(cls, db_document_collection):
        if db_document_collection is None:
            return None
        
        return cls(
            id=db_document_collection.id,
            collection_name=db_document_collection.collection_name,
            record_created=db_document_collection.record_created,
            documents=db_document_collection.documents,
            files=db_document_collection.files
        )

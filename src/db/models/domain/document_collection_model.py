from src.db.database.models import DocumentCollection

class DocumentCollectionModel:
    def __init__(self, id, collection_name, collection_type, record_created=None):
        self.id = id
        self.collection_name = collection_name
        self.record_created = record_created
        self.collection_type = collection_type

    def to_database_model(self):
        return DocumentCollection(
            id=self.id,
            collection_name=self.collection_name,
            record_created=self.record_created,
            collection_type=self.collection_type,
        )

    @classmethod
    def from_database_model(cls, db_document_collection):
        if db_document_collection is None:
            return None
        
        return cls(
            id=db_document_collection.id,
            collection_name=db_document_collection.collection_name,
            record_created=db_document_collection.record_created,
            collection_type=db_document_collection.collection_type,
        )

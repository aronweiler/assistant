from src.db.database.tables import DocumentCollection

class DocumentCollectionModel:
    def __init__(self, id, collection_name, embedding_name, record_created=None):
        self.id = id
        self.collection_name = collection_name
        self.record_created = record_created
        self.embedding_name = embedding_name

    def to_database_model(self):
        return DocumentCollection(
            id=self.id,
            collection_name=self.collection_name,
            record_created=self.record_created,
            embedding_name=self.embedding_name,
        )

    @classmethod
    def from_database_model(cls, db_document_collection):
        if db_document_collection is None:
            return None
        
        return cls(
            id=db_document_collection.id,
            collection_name=db_document_collection.collection_name,
            record_created=db_document_collection.record_created,
            embedding_name=db_document_collection.embedding_name,
        )

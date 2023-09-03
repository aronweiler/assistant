from db.database.models import File

class FileModel:
    def __init__(self, collection_id, user_id, file_name, id = None, file_classification=None,
                 file_summary=None, record_created=None):
        self.id = id
        self.collection_id = collection_id
        self.user_id = user_id
        self.file_name = file_name
        self.file_classification = file_classification
        self.file_summary = file_summary
        self.record_created = record_created

    def to_database_model(self):
        return File(
            id=self.id,
            collection_id=self.collection_id,
            user_id=self.user_id,
            file_name=self.file_name,
            file_classification=self.file_classification,
            file_summary=self.file_summary,
            record_created=self.record_created
        )

    @classmethod
    def from_database_model(cls, db_file):
        return cls(
            id=db_file.id,
            collection_id=db_file.collection_id,
            user_id=db_file.user_id,
            file_name=db_file.file_name,
            file_classification=db_file.file_classification,
            file_summary=db_file.file_summary,
            record_created=db_file.record_created
        )

from src.db.database.tables import CodeFile


class CodeFileModel:
    def __init__(
        self,
        code_file_name,
        code_file_sha,
        code_file_content,
        id=None,
        code_file_summary=None,
        record_created=None,
    ):
        self.id = id
        self.code_file_name = code_file_name
        self.code_file_sha = code_file_sha
        self.code_file_content = code_file_content
        self.code_file_summary = code_file_summary
        self.record_created = record_created

    def to_database_model(self):
        return CodeFile(
            id=self.id,
            code_file_name=self.code_file_name,
            code_file_sha=self.code_file_sha,
            code_file_content=self.code_file_content,
            code_file_summary=self.code_file_summary,
            record_created=self.record_created,
        )

    @classmethod
    def from_database_model(cls, db_code_file):
        if not db_code_file:
            return None
        return cls(
            id=db_code_file.id,
            code_file_name=db_code_file.code_file_name,
            code_file_sha=db_code_file.code_file_sha,
            code_file_content=db_code_file.code_file_content,
            code_file_summary=db_code_file.code_file_summary,
            record_created=db_code_file.record_created,
        )

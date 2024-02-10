from src.db.database.tables import CodeFileDependencies


class CodeFileDependenciesModel:
    def __init__(self, code_file_id, dependency_name, id=None):
        self.id = id
        self.code_file_id = code_file_id
        self.dependency_name = dependency_name

    def to_database_model(self):
        return CodeFileDependencies(
            id=self.id,
            code_file_id=self.code_file_id,
            dependency_name=self.dependency_name,
        )

    @classmethod
    def from_database_model(cls, db_dependency):
        if not db_dependency:
            return None
        return cls(
            id=db_dependency.id,
            code_file_id=db_dependency.code_file_id,
            dependency_name=db_dependency.dependency_name,
        )

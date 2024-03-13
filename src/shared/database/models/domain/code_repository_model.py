from src.shared.database.schema.tables import CodeRepository


class CodeRepositoryModel:
    def __init__(self, id, code_repository_address, branch_name, last_scanned = None, record_created=None):
        self.id = id
        self.code_repository_address = code_repository_address
        self.branch_name = branch_name
        self.last_scanned = last_scanned
        self.record_created = record_created
        

    def to_database_model(self):
        return CodeRepository(
            id=self.id,
            code_repository_address=self.code_repository_address,
            branch_name=self.branch_name,
            last_scanned = self.last_scanned,
            record_created=self.record_created,
        )

    @classmethod
    def from_database_model(cls, db_code_repository):
        if db_code_repository is None:
            return None

        return cls(
            id=db_code_repository.id,
            code_repository_address=db_code_repository.code_repository_address,
            branch_name=db_code_repository.branch_name,
            last_scanned = db_code_repository.last_scanned,
            record_created=db_code_repository.record_created,
        )

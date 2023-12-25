import sys
import os
from datetime import datetime

from typing import List, Any

from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import func, select, column, cast, or_

import pgvector.sqlalchemy

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.db.models.domain.code_repository_model import CodeRepositoryModel
from src.db.models.domain.code_file_model import CodeFileModel

from src.db.database.tables import CodeRepository, CodeFile

from src.db.models.vector_database import VectorDatabase, SearchType
from src.db.models.domain.document_collection_model import DocumentCollectionModel
from src.db.models.domain.document_model import DocumentModel
from src.db.models.domain.file_model import FileModel

from src.ai.embeddings_helper import get_embedding, get_embedding_with_model


class Code(VectorDatabase):
    def get_repositories(self) -> List[CodeRepositoryModel]:
        with self.session_context(self.Session()) as session:
            repositories = session.query(
                CodeRepository.id,
                CodeRepository.code_repository_address,
                CodeRepository.branch_name,
                CodeRepository.last_scanned,
                CodeRepository.record_created,
            ).all()

            return [CodeRepositoryModel.from_database_model(c) for c in repositories]
        
    def get_repository(self, code_repo_id: int) -> CodeRepositoryModel:
        if code_repo_id is None or int(code_repo_id) == -1:
            return None
        
        with self.session_context(self.Session()) as session:
            repository = session.query(
                CodeRepository.id,
                CodeRepository.code_repository_address,
                CodeRepository.branch_name,
                CodeRepository.last_scanned,
                CodeRepository.record_created,
            ).filter(
                CodeRepository.id == code_repo_id
            ).one()

            return CodeRepositoryModel.from_database_model(repository)

    def add_repository(self, address: str, branch_name: str):
        with self.session_context(self.Session()) as session:
            session.add(
                CodeRepository(
                    code_repository_address=address,
                    branch_name=branch_name,
                )
            )

    def update_last_scanned(self, code_repo_id: int, last_scanned: datetime):
        with self.session_context(self.Session()) as session:
            session.query(CodeRepository).filter(
                CodeRepository.id == code_repo_id
            ).update(
                {
                    CodeRepository.last_scanned: last_scanned,
                }
            )
            session.commit()


    def add_code(self, file_path:str, code:str, keywords_and_descriptions:dict):
        with self.session_context(self.Session()) as session:
            session.add(
                CodeFile(
                    file_path=file_path,
                    code=code,
                    keywords_and_descriptions=keywords_and_descriptions,
                )
            )
import logging
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

from src.db.database.tables import (
    CodeDescription,
    CodeKeyword,
    CodeRepository,
    CodeFile,
)

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
            repository = (
                session.query(
                    CodeRepository.id,
                    CodeRepository.code_repository_address,
                    CodeRepository.branch_name,
                    CodeRepository.last_scanned,
                    CodeRepository.record_created,
                )
                .filter(CodeRepository.id == code_repo_id)
                .one()
            )

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

    def code_file_exists(self, code_repo_id: int, code_file_name:str, file_sha: str) -> bool:
        with self.session_context(self.Session()) as session:
            return (
                session.query(CodeFile)
                .filter(CodeFile.code_repository_id == code_repo_id)
                .filter(CodeFile.code_file_name == code_file_name)
                .filter(CodeFile.code_file_sha == file_sha)
                .count()
                > 0
            )

    def add_update_code(
        self,
        repository_id,
        file_name: str,
        file_sha: str,
        file_content: str,
        file_summary: str,
        keywords_and_descriptions: dict,
    ):
        # Create the code file, adding the keywords and the descriptions as well
        with self.session_context(self.Session()) as session:
            
            # If the code file already exists, then update it
            existing_code_file = (
                session.query(CodeFile)
                .filter(CodeFile.code_repository_id == repository_id)
                .filter(CodeFile.code_file_name == file_name)
                .one_or_none()
            )
            
            if existing_code_file:                
                if existing_code_file.code_file_sha == file_sha:
                    # The file has not changed, so we don't need to update it
                    logging.info(f"Code file {file_name} has not changed, so we don't need to update it")
                    return
                
                logging.info(f"Code file {file_name} has changed, so we need to update it")
                
                existing_code_file.code_file_sha = file_sha
                existing_code_file.code_file_content = file_content
                existing_code_file.code_file_summary = file_summary
                existing_code_file.code_file_summary_embedding = get_embedding(
                    text=file_summary,
                    collection_type="Remote",
                    instruction="Represent the summary for retrieval: ",
                )
                
                session.add(existing_code_file)
                session.commit()
                
                # Delete the existing keywords and descriptions
                session.query(CodeKeyword).filter(
                    CodeKeyword.code_file_id == existing_code_file.id
                ).delete()
                session.query(CodeDescription).filter(
                    CodeDescription.code_file_id == existing_code_file.id
                ).delete()
                session.commit()
            else:
                logging.info(f"Code file {file_name} does not exist, so we need to create it")
                
                # Create the code file
                code_file = CodeFile(
                    code_repository_id=repository_id,
                    code_file_name=file_name,
                    code_file_sha=file_sha,
                    code_file_content=file_content,
                    code_file_summary=file_summary,
                    # TODO: Implement embedding model selection for code
                    code_file_summary_embedding=get_embedding(
                        text=file_summary,
                        collection_type="Remote",
                        instruction="Represent the summary for retrieval: ",
                    ) if file_summary.strip() != "" else None,
                )
                session.add(code_file)            
                session.commit()

            for keyword in keywords_and_descriptions["keywords"]:
                code_keyword = CodeKeyword(code_file_id=code_file.id, keyword=keyword)

                session.add(code_keyword)
                session.commit()

            for description in keywords_and_descriptions["descriptions"]:
                code_description = CodeDescription(
                    code_file_id=code_file.id,
                    description_text=description,
                    description_text_embedding=get_embedding(
                        text=description,
                        collection_type="Remote",
                        instruction="Represent the description for retrieval: ",
                    ),
                )

                session.add(code_description)
                session.commit()

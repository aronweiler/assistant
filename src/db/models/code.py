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
    code_repository_files_association,
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

    def code_file_exists(
        self, code_file_name: str, file_sha: str
    ) -> bool:
        with self.session_context(self.Session()) as session:
            # We now need to join CodeFile with the association table and then filter by repository ID
            return (
                session.query(CodeFile)
                .join(
                    code_repository_files_association,
                    CodeFile.id == code_repository_files_association.c.code_file_id,
                )
                .filter(CodeFile.code_file_name == code_file_name)
                .filter(CodeFile.code_file_sha == file_sha)
                .count()
                > 0
            )

    def link_code_file_to_repo(self, code_file_id: int, code_repo_id: int):
        with self.session_context(self.Session()) as session:
            # Link the code file with the repository
            assoc_entry = {
                "code_repository_id": code_repo_id,
                "code_file_id": code_file_id,
            }

            session.execute(
                code_repository_files_association.insert().values(**assoc_entry)
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
        # Create or update the code file, adding the keywords and descriptions as well
        with self.session_context(self.Session()) as session:
            # Check if the code file already exists regardless of repository
            existing_code_file = (
                session.query(CodeFile)
                .filter(CodeFile.code_file_name == file_name)
                .filter(CodeFile.code_file_sha == file_sha)
                .one_or_none()
            )

            if existing_code_file:
                logging.info(f"Code file {file_name} already exists.")

                # Check if this repository is already linked to this code file
                link_exists = (
                    session.query(code_repository_files_association)
                    .filter_by(
                        code_repository_id=repository_id,
                        code_file_id=existing_code_file.id,
                    )
                    .count()
                    > 0
                )

                if not link_exists:
                    # Link the existing code file with the new repository
                    assoc_entry = {
                        "code_repository_id": repository_id,
                        "code_file_id": existing_code_file.id,
                    }
                    session.execute(
                        code_repository_files_association.insert().values(**assoc_entry)
                    )
                    session.commit()

                    # If the file exists, we don't need to update the keywords and descriptions
                    return

            else:
                logging.info(f"Creating a new entry for code file {file_name}.")

                # Create a new CodeFile instance since it doesn't exist yet
                new_code_file = CodeFile(
                    code_file_name=file_name,
                    code_file_sha=file_sha,
                    code_file_content=file_content,
                    code_file_summary=file_summary,
                    # TODO: Implement embedding model selection for code
                    code_file_summary_embedding=get_embedding(
                        text=file_summary,
                        collection_type="Remote",
                        instruction="Represent the summary for retrieval: ",
                    )
                    if file_summary.strip() != ""
                    else None,
                )

                session.add(new_code_file)
                session.flush()  # Flush to assign an ID to new_code_file

                # Link the new code file with the repository
                assoc_entry = {
                    "code_repository_id": repository_id,
                    "code_file_id": new_code_file.id,
                }

                session.execute(
                    code_repository_files_association.insert().values(**assoc_entry)
                )

                code_file_id = new_code_file.id

            for keyword in keywords_and_descriptions["keywords"]:
                code_keyword = CodeKeyword(code_file_id=code_file_id, keyword=keyword)

                session.add(code_keyword)
                session.commit()

            for description in keywords_and_descriptions["descriptions"]:
                code_description = CodeDescription(
                    code_file_id=code_file_id,
                    description_text=description,
                    description_text_embedding=get_embedding(
                        text=description,
                        collection_type="Remote",
                        instruction="Represent the description for retrieval: ",
                    ),
                )

                session.add(code_description)
                session.commit()

    def get_code_file(self, code_repo_id: int, code_file_name: str) -> CodeFileModel:
        with self.session_context(self.Session()) as session:
            # Join CodeFile with the association table and filter by repository ID and file name
            code_file = (
                session.query(
                    CodeFile.id,
                    CodeFile.code_file_name,
                    CodeFile.code_file_sha,
                    CodeFile.code_file_content,
                    CodeFile.code_file_summary,
                    CodeFile.code_file_summary_embedding,
                    CodeFile.code_file_valid,
                    CodeFile.record_created,
                )
                .join(
                    code_repository_files_association,
                    CodeFile.id == code_repository_files_association.c.code_file_id,
                )
                .filter(
                    code_repository_files_association.c.code_repository_id
                    == code_repo_id
                )
                .filter(CodeFile.code_file_name == code_file_name)
                .one_or_none()
            )

            return CodeFileModel.from_database_model(code_file) if code_file else None

    def get_code_file_id(self, code_file_name: str, file_sha:str) -> int:
        with self.session_context(self.Session()) as session:
            code_file = (
                session.query(
                    CodeFile.id,
                )
                .filter(CodeFile.code_file_name == code_file_name)
                .filter(CodeFile.code_file_sha == file_sha)
                .one_or_none()
            )

            return code_file.id if code_file else None            

    def unlink_code_files(self, code_repo_id: int):
        with self.session_context(self.Session()) as session:
            # Unlink the code files from the repository
            session.query(code_repository_files_association).filter(
                code_repository_files_association.c.code_repository_id == code_repo_id
            ).delete(synchronize_session="fetch")
            session.commit()

    def update_code_file_valid(self, id: int, code_file_valid: bool):
        with self.session_context(self.Session()) as session:
            # Update the valid status of a specific code file by its ID
            session.query(CodeFile).filter(CodeFile.id == id).update(
                {CodeFile.code_file_valid: code_file_valid}, synchronize_session="fetch"
            )
            session.commit()

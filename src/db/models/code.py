import logging
import sys
import os
from datetime import datetime

from typing import List, Any
from urllib.parse import urlparse
from requests import Session

from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import and_, func, select, column, cast, or_

import pgvector.sqlalchemy
from src.ai.prompts.prompt_models.code_details_extraction import (
    CodeDetailsExtractionOutput,
)

from src.db.models.domain.source_control_provider_model import (
    SourceControlProviderModel,
    SupportedSourceControlProviderModel,
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.db.models.domain.code_repository_model import CodeRepositoryModel
from src.db.models.domain.code_file_model import CodeFileModel

from src.db.database.tables import (
    CodeDescription,
    CodeFileDependencies,
    CodeKeyword,
    CodeRepository,
    CodeFile,
    SourceControlProvider,
    SupportedSourceControlProvider,
    code_repository_files_association,
)

from src.db.models.vector_database import VectorDatabase, SearchType
from src.db.models.domain.document_collection_model import DocumentCollectionModel
from src.db.models.domain.document_model import DocumentModel
from src.db.models.domain.file_model import FileModel

from src.ai.utilities.embeddings_helper import get_embedding, get_embedding_with_model


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
            # Check if the repository already exists
            existing_repository = (
                session.query(CodeRepository)
                .filter(CodeRepository.code_repository_address == address)
                .filter(CodeRepository.branch_name == branch_name)
                .one_or_none()
            )

            if existing_repository:
                logging.info(
                    f"Repository {address} on branch {branch_name} already exists."
                )
                return

            # Add the new repository since it does not exist
            session.add(
                CodeRepository(
                    code_repository_address=address,
                    branch_name=branch_name,
                )
            )
            session.commit()

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

    def code_file_exists(self, code_file_name: str, file_sha: str) -> bool:
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
        keywords_and_descriptions: CodeDetailsExtractionOutput,
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
                    return existing_code_file.id

            else:
                logging.info(f"Creating a new entry for code file {file_name}.")

                # Create a new CodeFile instance since it doesn't exist yet
                new_code_file = CodeFile(
                    code_file_name=file_name,
                    code_file_sha=file_sha,
                    code_file_content=file_content,
                    code_file_summary=file_summary,
                    # TODO: Implement embedding model selection for code
                    code_file_summary_embedding=(
                        get_embedding(
                            text=file_summary,
                            collection_type="Remote",
                            instruction="Represent the summary for retrieval: ",
                        )
                        if file_summary.strip() != ""
                        else None
                    ),
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

            if keywords_and_descriptions:
                for keyword in keywords_and_descriptions.keywords:
                    code_keyword = CodeKeyword(
                        code_file_id=code_file_id, keyword=keyword
                    )

                    session.add(code_keyword)
                    session.commit()

                for description in keywords_and_descriptions.descriptions:
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
                    
            return code_file_id

    def get_code_files(self, repository_id: int) -> List[CodeFileModel]:
        with self.session_context(self.Session()) as session:
            # We now need to join CodeFile with the association table and then filter by repository ID
            code_files = (
                session.query(
                    CodeFile.id,
                    CodeFile.code_file_name,
                    CodeFile.code_file_sha,
                    CodeFile.code_file_content,
                    CodeFile.code_file_summary,
                    CodeFile.code_file_summary_embedding,
                    CodeFile.record_created,
                )
                .join(
                    code_repository_files_association,
                    CodeFile.id == code_repository_files_association.c.code_file_id,
                )
                .filter(
                    code_repository_files_association.c.code_repository_id
                    == repository_id
                )
                .all()
            )

            return [CodeFileModel.from_database_model(c) for c in code_files]

    def get_code_file_by_id(self, code_file_id: int) -> CodeFileModel:
        with self.session_context(self.Session()) as session:
            # We now need to join CodeFile with the association table and then filter by repository ID
            code_file = (
                session.query(
                    CodeFile.id,
                    CodeFile.code_file_name,
                    CodeFile.code_file_sha,
                    CodeFile.code_file_content,
                    CodeFile.code_file_summary,
                    CodeFile.code_file_summary_embedding,
                    CodeFile.record_created,
                )
                .filter(CodeFile.id == code_file_id)
                .one_or_none()
            )

            return CodeFileModel.from_database_model(code_file) if code_file else None

    def get_code_files_by_partial_name(
        self, repository_id: int, partial_file_name: str
    ) -> List[CodeFileModel]:
        with self.session_context(self.Session()) as session:
            # We now need to join CodeFile with the association table and then filter by repository ID
            code_files = (
                session.query(
                    CodeFile.id,
                    CodeFile.code_file_name,
                    CodeFile.code_file_sha,
                    CodeFile.code_file_content,
                    CodeFile.code_file_summary,
                    CodeFile.code_file_summary_embedding,
                    CodeFile.record_created,
                )
                .join(
                    code_repository_files_association,
                    CodeFile.id == code_repository_files_association.c.code_file_id,
                )
                .filter(
                    code_repository_files_association.c.code_repository_id
                    == repository_id
                )
                .filter(CodeFile.code_file_name.contains(partial_file_name))
                .all()
            )

            return [CodeFileModel.from_database_model(c) for c in code_files]

    def add_code_file_dependency(self, code_file_id, dependency_name):
        with self.session_context(self.Session()) as session:
            session.add(
                CodeFileDependencies(
                    code_file_id=code_file_id, dependency_name=dependency_name
                )
            )
            session.commit()

    def get_code_file_dependencies(self, code_file_id):
        with self.session_context(self.Session()) as session:
            dependencies = (
                session.query(CodeFileDependencies)
                .filter(CodeFileDependencies.code_file_id == code_file_id)
                .all()
            )
            return [dependency.dependency_name for dependency in dependencies]

    def get_code_file_by_name(
        self, code_repo_id: int, code_file_name: str
    ) -> CodeFileModel:
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

    def get_code_file_id(self, code_file_name: str, file_sha: str) -> int:
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

    def get_code_file_keywords(self, code_file_id: int) -> List[str]:
        with self.session_context(self.Session()) as session:
            keywords = (
                session.query(CodeKeyword.keyword)
                .filter(CodeKeyword.code_file_id == code_file_id)
                .all()
            )

            return [keyword.keyword for keyword in keywords]

    def get_code_file_descriptions(self, code_file_id: int) -> List[str]:
        with self.session_context(self.Session()) as session:
            descriptions = (
                session.query(CodeDescription.description_text)
                .filter(CodeDescription.code_file_id == code_file_id)
                .all()
            )

            return [description.description_text for description in descriptions]

    def unlink_code_files(self, code_repo_id: int):
        with self.session_context(self.Session()) as session:
            # Unlink the code files from the repository
            session.query(code_repository_files_association).filter(
                code_repository_files_association.c.code_repository_id == code_repo_id
            ).delete(synchronize_session="fetch")
            session.commit()

    def get_code_files_by_folder(
        self, repository_id: int, folder_path: str
    ) -> List[CodeFileModel]:
        """Retrieves all code files from the database that reside in a specified folder.

        Args:
            repository_id (int): The ID of the repository.
            folder_path (str): The path of the folder within the repository.

        Returns:
            List[CodeFileModel]: A list of CodeFileModel instances representing the code files.
        """
        with self.session_context(self.Session()) as session:
            # We need to join CodeFile with the association table and then filter by repository ID and folder path
            code_files = (
                session.query(
                    CodeFile.id,
                    CodeFile.code_file_name,
                    CodeFile.code_file_sha,
                    CodeFile.code_file_content,
                    CodeFile.code_file_summary,
                    CodeFile.code_file_summary_embedding,
                    CodeFile.record_created,
                )
                .join(
                    code_repository_files_association,
                    CodeFile.id == code_repository_files_association.c.code_file_id,
                )
                .filter(
                    code_repository_files_association.c.code_repository_id
                    == repository_id,
                    CodeFile.code_file_name.like(f"{folder_path}/%"),
                )
                .all()
            )

            return [CodeFileModel.from_database_model(c) for c in code_files]

    def search_code_files(
        self,
        repository_id: int,
        similarity_query: str,
        keywords: List[str],
        top_k=10,
        exclude_file_names: List[str] = [],
    ) -> List[CodeFileModel]:
        with self.session_context(self.Session()) as session:
            if similarity_query.strip() != "":
                # Perform similarity search on CodeFile.code_file_summary_embedding
                code_file_similarity_results = self._get_similarity_results(
                    session,
                    repository_id,
                    CodeFile.code_file_summary_embedding,
                    similarity_query,
                    top_k,
                    exclude_file_names,
                )

                # Perform similarity search on CodeDescription.description_text_embedding
                code_description_similarity_results = self._get_similarity_results(
                    session,
                    repository_id,
                    CodeDescription.description_text_embedding,
                    similarity_query,
                    top_k,
                    exclude_file_names,
                )
            else:
                code_file_similarity_results = []
                code_description_similarity_results = []

            if keywords != []:
                # Perform keyword search on CodeKeywords.keyword
                keyword_search_results = self._get_keyword_search_results(
                    session, repository_id, keywords, top_k, exclude_file_names
                )
            else:
                keyword_search_results = []

            # Combine results from the three searches
            combined_results = (
                code_file_similarity_results + code_description_similarity_results
            )

            # Sort combined results by relevance
            sorted_combined_results = sorted(
                combined_results,
                key=lambda x: (
                    x[1] if x[1] is not None else 0.5
                ),  # Assuming the second element is the relevance score, handling none for keyword search (not in this list anymore, but keeping this)
                reverse=False,  # Assuming lower scores indicate higher relevance
            )

            # Create a unique list of code files, always keeping the first result
            unique_results = []
            unique_ids = []
            for result in sorted_combined_results:
                if result[0].id not in unique_ids:
                    unique_results.append(result)
                    unique_ids.append(result[0].id)

            # Prepend the keyword search results to the unique list, but only if the id is not already in the list
            # Keyword results are inserted because they are the most relevant
            for result in keyword_search_results:
                if result[0].id not in unique_ids:
                    unique_results.insert(0, result)
                    unique_ids.append(result[0].id)

            # Return the top_k results as CodeFileModel objects
            return [
                CodeFileModel.from_database_model(result[0])
                for result in unique_results[:top_k]
            ]

    def _get_similarity_results(
        self,
        session: Session,
        repository_id: int,
        embedding_column,
        similarity_query,
        top_k: int,
        exclude_file_names: List[str] = [],
    ):
        query_embedding = get_embedding(
            text=similarity_query,
            collection_type="Remote",
            instruction="Represent the query for retrieval: ",
        )

        emb_val = cast(query_embedding, pgvector.sqlalchemy.Vector)
        cosine_distance = func.cosine_distance(embedding_column, emb_val)

        statement = (
            select(CodeFile)
            .join(
                code_repository_files_association,
                CodeFile.id == code_repository_files_association.c.code_file_id,
            )
            .filter(
                code_repository_files_association.c.code_repository_id == repository_id
            )
            .filter(~CodeFile.code_file_name.in_(exclude_file_names))
            .order_by(cosine_distance)
            .limit(top_k)
            .add_columns(cosine_distance)
        )
        result = session.execute(statement).fetchall()

        return [(code_file, distance) for code_file, distance in result]

    def _get_keyword_search_results(
        self,
        session: Session,
        repository_id: int,
        keywords: List[str],
        top_k: int,
        exclude_file_names: List[str] = [],
    ) -> List[CodeFileModel]:
        # Query the code_files table for matches in the code_content field
        code_content_matches = (
            session.query(CodeFile)
            .filter(
                CodeFile.code_repositories.any(id=repository_id),
                or_(
                    *[
                        CodeFile.code_file_content.like(f"%{keyword}%")
                        for keyword in keywords
                    ]
                ),
            )
            .filter(~CodeFile.code_file_name.in_(exclude_file_names))
            .limit(top_k)
            .all()
        )

        # Query the code_keywords table for matches in the keyword field
        keyword_matches = (
            session.query(CodeFile)
            .join(CodeKeyword, CodeFile.id == CodeKeyword.code_file_id)
            .filter(
                CodeFile.code_repositories.any(id=repository_id),
                or_(
                    *[CodeKeyword.keyword.like(f"%{keyword}%") for keyword in keywords]
                ),
            )
            .limit(top_k)
            .all()
        )

        # Combine the results and remove duplicates
        combined_results = list(set(code_content_matches + keyword_matches))

        # Return the top_k results as CodeFileModel objects
        return [
            (CodeFileModel.from_database_model(code_file), None)
            for code_file in combined_results[:top_k]
        ]  # No distance for keyword search

    # Add a function to add a supported source control provider
    def add_supported_source_control_provider(self, name):
        with self.session_context(self.Session()) as session:
            session.add(SupportedSourceControlProvider(name=name))
            session.commit()

    # Add a function to retrieve supported source control providers
    def get_supported_source_control_providers(self):
        with self.session_context(self.Session()) as session:
            providers = session.query(SupportedSourceControlProvider).all()
            return [
                SupportedSourceControlProviderModel.from_database_model(provider)
                for provider in providers
            ]

    def get_supported_source_control_provider_by_id(self, id):
        with self.session_context(self.Session()) as session:
            provider = (
                session.query(SupportedSourceControlProvider)
                .filter(SupportedSourceControlProvider.id == id)
                .one_or_none()
            )
            return (
                SupportedSourceControlProviderModel.from_database_model(provider)
                if provider
                else None
            )

    def get_supported_source_control_provider_by_name(self, name):
        with self.session_context(self.Session()) as session:
            provider = (
                session.query(SupportedSourceControlProvider)
                .filter(SupportedSourceControlProvider.name == name)
                .one_or_none()
            )
            return (
                SupportedSourceControlProviderModel.from_database_model(provider)
                if provider
                else None
            )

    # Add a function to add a source control provider
    def add_source_control_provider(
        self,
        supported_source_control_provider: SupportedSourceControlProviderModel,
        name,
        url,
        requires_auth,
        access_token,
    ):

        if self.get_source_control_provider_by_name(name):
            raise Exception(
                f"A source control provider with the name {name} already exists."
            )

        if self.get_provider_from_url(url):
            raise Exception(
                f"A source control provider with the same domain '{self._get_domain_name(url)}' already exists."
            )

        with self.session_context(self.Session()) as session:
            session.add(
                SourceControlProvider(
                    supported_source_control_provider_id=supported_source_control_provider.id,
                    source_control_provider_name=name,
                    source_control_provider_url=url,
                    requires_authentication=requires_auth,
                    source_control_access_token=access_token or None,
                )
            )
            session.commit()

    # Add a function to update a source control provider
    def update_source_control_provider(
        self,
        id,
        supported_source_control_provider: SupportedSourceControlProviderModel,
        name,
        url,
        requires_auth,
        access_token,
    ):
        with self.session_context(self.Session()) as session:
            session.query(SourceControlProvider).filter(
                SourceControlProvider.id == id
            ).update(
                {
                    SourceControlProvider.supported_source_control_provider_id: supported_source_control_provider.id,
                    SourceControlProvider.source_control_provider_name: name,
                    SourceControlProvider.source_control_provider_url: url,
                    SourceControlProvider.requires_authentication: requires_auth,
                    SourceControlProvider.source_control_access_token: access_token,
                }
            )
            session.commit()

    # Add a function to delete a source control provider
    def delete_source_control_provider(self, id):
        with self.session_context(self.Session()) as session:
            session.query(SourceControlProvider).filter(
                SourceControlProvider.id == id
            ).delete()
            session.commit()

    # Add a function to retrieve all source control providers
    def get_all_source_control_providers(self):
        with self.session_context(self.Session()) as session:
            providers = session.query(SourceControlProvider).all()
            return [
                SourceControlProviderModel.from_database_model(provider)
                for provider in providers
            ]

    # Add a function to retrieve a single source control provider
    def get_source_control_provider(self, id):
        with self.session_context(self.Session()) as session:
            provider = (
                session.query(SourceControlProvider)
                .filter(SourceControlProvider.id == id)
                .one_or_none()
            )
            return (
                SourceControlProviderModel.from_database_model(provider)
                if provider
                else None
            )

    def get_source_control_provider_by_name(self, name):
        with self.session_context(self.Session()) as session:
            provider = (
                session.query(SourceControlProvider)
                .filter(SourceControlProvider.source_control_provider_name == name)
                .one_or_none()
            )
            return (
                SourceControlProviderModel.from_database_model(provider)
                if provider
                else None
            )

    def get_provider_from_url(self, url: str):
        """
        Returns the source control provider from a URL.

        :param url: The URL to parse.
        :return: The source control provider.
        """
        # Find the source control provider that starts with the URL (case insensitive)
        providers = self.get_all_source_control_providers()

        domain = self._get_domain_name(url)

        for provider in providers:
            if (
                domain.lower()
                == self._get_domain_name(provider.source_control_provider_url).lower()
            ):
                return SourceControlProviderModel.from_database_model(provider)

        return None

    def _get_domain_name(self, url):
        try:
            # Parse the URL and extract the netloc part which contains the domain name
            parsed_url = urlparse(url)
            # Split the netloc by '.' and take the last two parts as domain
            # This works for most common URLs
            domain_parts = parsed_url.netloc.split(".")
            domain = ".".join(domain_parts[-2:])
            return domain
        except Exception as e:
            print(f"An error occurred: {e}")
            return None


# Testing
if __name__ == "__main__":
    code = Code()

    # Test get_repositories
    repositories = code.get_repositories()
    print(repositories)

    # Test searching for code
    code_files = code.search_code_files(
        1,
        "What is the meaning of the Auto setting on the UI?",
        ["Auto", "UI", "Setting"],
        20,
    )

    print(
        "\n\n".join(
            [
                f"{cf.code_file_name} summary:\n{cf.code_file_summary}"
                for cf in code_files
            ]
        )
    )

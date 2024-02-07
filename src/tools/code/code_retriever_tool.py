import sys
import os
from typing import List, Union

# Importing necessary modules and classes for the tool.
from src.ai.tools.tool_registry import register_tool, tool_class
from src.db.models.code import Code

# Adjusting system path to include the root directory for module imports.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Importing database models and utilities.
from src.ai.conversations.conversation_manager import ConversationManager

# Importing integration modules for GitLab and GitHub.
from src.integrations.gitlab.gitlab_retriever import GitlabRetriever

from src.integrations.github.github_retriever import GitHubRetriever


@tool_class
class CodeRetrieverTool:
    # Mapping of source control provider names to their respective retriever classes.
    source_control_to_retriever_map = {
        "gitlab": GitlabRetriever,
        "github": GitHubRetriever,
    }

    def __init__(
        self, configuration, conversation_manager: ConversationManager
    ) -> None:
        self.configuration = configuration
        self.conversation_manager = conversation_manager

    def get_branches(self, url: str) -> List[str]:
        """
        Retrieves branches from a given URL using the appropriate source control provider.

        :param url: The URL from which to retrieve the branches.
        :return: The retrieved branches or an error message if retrieval is not supported.
        """
        # Get the corresponding retriever instance
        retriever_instance = self.get_retriever_instance(url)

        # Use the instantiated retriever to fetch branches from the provided URL.
        return retriever_instance.retrieve_branches(url=url)

    def scan_repo(self, url: str, branch_name: str) -> List[str]:
        """
        Scans a given URL using the appropriate source control provider.

        :param url: The URL from which to scan the repo.
        :return: The retrieved file paths or an error message if retrieval is not supported.
        """
        # Get the corresponding retriever instance
        retriever_instance = self.get_retriever_instance(url)

        # Use the instantiated retriever to fetch branches from the provided URL.
        files = retriever_instance.scan_repository(url=url, branch_name=branch_name)

        # TODO: Verify this works with whatever gitlab is doing
        return files

    def get_code_from_repo_and_branch(
        self, path: str, repo_address: str, branch_name: str
    ) -> str:
        """
        Retrieves code from a given repo using the appropriate source control provider.

        :param path: The path to the file from which to retrieve the code.
        :param repo_address: The address of the repo from which to retrieve the code.
        :param branch_name: The name of the branch from which to retrieve the code.
        :return: The retrieved code or an error message if retrieval is not supported.
        """
        # Assemble the URL from the repo address and branch name.
        url = f"{repo_address}/raw/{branch_name}/{path}"

        # Get the corresponding retriever instance
        retriever_instance = self.get_retriever_instance(url)

        # Use the instantiated retriever to fetch code from the provided URL.
        return retriever_instance.retrieve_code(
            path=path, repo_address=repo_address, branch_name=branch_name
        )

    @register_tool(
        display_name="Retrieve Source Code",
        requires_documents=False,
        description="Gets source code from a specified URL or a list of repository file IDs.",
        additional_instructions="Use this tool to get source code from a URL, or a file in the currently loaded repository. Make sure to understand and pass the correct argument (`url`, or `repository_file_ids`) based on the user's request.  If the user specifies a URL, do not use the loaded repository, instead pass the URL in here.",
        category="Code",
    )
    def retrieve_source_code(
        self, url: str = "", repository_file_ids: List[int] = None
    ) -> Union[str, List[str]]:
        if url:
            # Assuming get_retriever_instance and its dependencies are accessible
            retriever_instance = self.get_retriever_instance(url)
            try:
                return retriever_instance.retrieve_data(url=url)
            except Exception as e:
                return f"Error retrieving source code from URL. Exception: {e}"
        elif repository_file_ids:
            code_files = []
            for file_id in repository_file_ids:
                code_file = self.conversation_manager.code_helper.get_code_file_by_id(
                    file_id
                )
                if code_file is not None:
                    code_files.append(
                        f"**{code_file.code_file_name} (ID: {code_file.id})**\n```\n{code_file.code_file_content}\n```\n\n"
                    )
            if not code_files:
                return "Code file(s) with the provided IDs were not found."
            return "\n".join(code_files)
        else:
            return "Please provide either a URL or a list of file IDs."

    def get_retriever_instance(self, url):
        code_helper = Code()
        source_control_provider = code_helper.get_provider_from_url(url)

        if not source_control_provider:
            raise Exception(
                f"The URL {url} does not correspond to a configured source control provider."
            )

        supported_provider = code_helper.get_supported_source_control_provider_by_id(
            source_control_provider.supported_source_control_provider_id
        )

        # Get the corresponding retriever class from the map using provider name in lowercase.
        retriever_class = self.source_control_to_retriever_map.get(
            supported_provider.name.lower()
        )

        # If no retriever class is found, return an error message indicating unsupported code retrieval.
        if not retriever_class:
            raise f"Source control provider {source_control_provider.source_control_provider_name} does not support code retrieval"

        return retriever_class(
            source_control_pat=source_control_provider.source_control_access_token,
            source_control_url=source_control_provider.source_control_provider_url,
            requires_authentication=source_control_provider.requires_authentication,
        )

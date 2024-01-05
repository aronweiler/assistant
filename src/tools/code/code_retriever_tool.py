import sys
import os
from typing import List

# Importing necessary modules and classes for the tool.
from langchain.base_language import BaseLanguageModel
from src.ai.llm_helper import get_tool_llm
from src.ai.tools.tool_registry import register_tool, tool_class
from src.integrations.github import github_issue_creator
from src.tools.code.issue_tool import IssueTool

# Adjusting system path to include the root directory for module imports.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Importing database models and utilities.
from src.db.models.documents import Documents
from src.ai.conversations.conversation_manager import ConversationManager
from src.utilities.token_helper import num_tokens_from_string
from src.utilities.parsing_utilities import parse_json

# Importing integration modules for GitLab and GitHub.
from src.integrations.gitlab.gitlab_issue_creator import GitlabIssueCreator
from src.integrations.gitlab.gitlab_issue_retriever import GitlabIssueRetriever
from src.integrations.gitlab.gitlab_retriever import GitlabRetriever

from src.integrations.github.github_issue_creator import GitHubIssueCreator
from src.integrations.github.github_retriever import GitHubRetriever

@tool_class
class CodeRetrieverTool:
    # Mapping of source control provider names to their respective retriever classes.
    source_control_to_retriever_map = {
        "gitlab": GitlabRetriever,
        "github": GitHubRetriever,
    }

    def __init__(self):
        """
        Initializes the CodeRetrieverTool
        """

        # Constants for environment variables and source control providers
        self.source_control_provider = os.getenv(
            "SOURCE_CONTROL_PROVIDER", "github"
        ).lower()
        self.source_control_url = os.getenv("source_control_url")
        self.source_control_pat = os.getenv("source_control_pat")

    def get_branches(self, url: str) -> List[str]:
        """
        Retrieves branches from a given URL using the appropriate source control provider.

        :param url: The URL from which to retrieve the branches.
        :return: The retrieved branches or an error message if retrieval is not supported.
        """
        # Get the corresponding retriever class from the map using provider name in lowercase.
        retriever_class = self.source_control_to_retriever_map.get(
            self.source_control_provider
        )

        # If no retriever class is found, return an error message indicating unsupported branch retrieval.
        if not retriever_class:
            return [
                f"Source control provider {self.source_control_provider} does not support branch retrieval"
            ]

        # Instantiate the retriever with necessary credentials from environment variables.
        retriever_instance = retriever_class(
            self.source_control_url,
            self.source_control_pat,
        )

        # Use the instantiated retriever to fetch branches from the provided URL.
        return retriever_instance.retrieve_branches(url=url)

    def scan_repo(self, url: str, branch_name: str) -> List[str]:
        """
        Scans a given URL using the appropriate source control provider.

        :param url: The URL from which to scan the repo.
        :return: The retrieved file paths or an error message if retrieval is not supported.
        """
        # Get the corresponding retriever class from the map using provider name in lowercase.
        retriever_class = self.source_control_to_retriever_map.get(
            self.source_control_provider
        )

        # If no retriever class is found, return an error message indicating unsupported branch retrieval.
        if not retriever_class:
            return [
                f"Source control provider {self.source_control_provider} does not support branch retrieval"
            ]

        # Instantiate the retriever with necessary credentials from environment variables.
        retriever_instance = retriever_class(
            self.source_control_url,
            self.source_control_pat,
        )

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
        # Get the corresponding retriever class from the map using provider name in lowercase.
        retriever_class = self.source_control_to_retriever_map.get(
            self.source_control_provider
        )

        # If no retriever class is found, return an error message indicating unsupported code retrieval.
        if not retriever_class:
            return f"Source control provider {self.source_control_provider} does not support code retrieval"

        # Instantiate the retriever with necessary credentials from environment variables.
        retriever_instance = retriever_class(
            self.source_control_url,
            self.source_control_pat,
        )

        # Use the instantiated retriever to fetch code from the provided URL.
        return retriever_instance.retrieve_code(
            path=path, repo_address=repo_address, branch_name=branch_name
        )

    @register_tool(
        description="Gets source code from a specified URL",
        additional_instructions="Use this tool to get source code from a source control provider, such as GitHub or GitLab.",
    )
    def retrieve_source_code_from_url(self, url: str) -> str:
        """
        Retrieves source code from a given URL using the appropriate source control provider.

        :param url: The URL from which to retrieve the source code file.
        :return: The retrieved source code or an error message if retrieval is not supported.
        """
        # Get the corresponding retriever class from the map using provider name in lowercase.
        retriever_class = self.source_control_to_retriever_map.get(
            self.source_control_provider
        )

        # If no retriever class is found, return an error message indicating unsupported file retrieval.
        if not retriever_class:
            return f"Source control provider {self.source_control_provider} does not support file retrieval"

        # Instantiate the retriever with necessary credentials from environment variables.
        retriever_instance = retriever_class(
            self.source_control_url,
            self.source_control_pat,
        )

        # Use the instantiated retriever to fetch data from the provided URL.
        return retriever_instance.retrieve_data(url=url)

    def retrieve_source_code(self, url: str) -> str:
        """
        Retrieves source code from a given URL using the appropriate source control provider.

        :param url: The URL from which to retrieve the source code file.
        :return: The retrieved source code or an error message if retrieval is not supported.
        """
        # Get the corresponding retriever class from the map using provider name in lowercase.
        retriever_class = self.source_control_to_retriever_map.get(
            self.source_control_provider
        )

        # If no retriever class is found, return an error message indicating unsupported file retrieval.
        if not retriever_class:
            return f"Source control provider {self.source_control_provider} does not support file retrieval"

        # Instantiate the retriever with necessary credentials from environment variables.
        retriever_instance = retriever_class(
            self.source_control_url,
            self.source_control_pat,
        )

        # Use the instantiated retriever to fetch data from the provided URL.
        return retriever_instance.retrieve_data(url=url)

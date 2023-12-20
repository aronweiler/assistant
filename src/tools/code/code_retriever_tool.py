import sys
import os
from typing import List

# Importing necessary modules and classes for the tool.
from langchain.base_language import BaseLanguageModel
from src.ai.llm_helper import get_tool_llm
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


class CodeRetrieverTool:
    # Mapping of source control provider names to their respective retriever classes.
    source_control_to_retriever_map = {
        "gitlab": GitlabRetriever,
        "github": GitHubRetriever,
    }

    def __init__(
        self,
        configuration,
        conversation_manager: ConversationManager,
    ):
        """
        Initializes the CodeRetrieverTool with a given configuration and an conversation manager.

        :param configuration: Configuration settings for the tool.
        :param conversation_manager: The manager that handles interactions with language models.
        """
        self.configuration = configuration
        self.conversation_manager = conversation_manager

        # Constants for environment variables and source control providers
        self.source_control_provider = os.getenv(
            "SOURCE_CONTROL_PROVIDER", "github"
        ).lower()
        self.source_control_url = os.getenv("source_control_url")
        self.source_control_pat = os.getenv("source_control_pat")

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

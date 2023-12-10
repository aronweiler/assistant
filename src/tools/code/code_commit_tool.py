import sys
import os
from typing import List

# Importing necessary modules and classes for the tool.
from langchain.base_language import BaseLanguageModel

# Adjusting system path to include the root directory for module imports.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.ai.llm_helper import get_tool_llm
from src.integrations.github import github_issue_creator
from src.tools.code.issue_tool import IssueTool


# Importing database models and utilities.
from src.db.models.documents import Documents
from src.ai.interactions.interaction_manager import InteractionManager
from src.utilities.token_helper import num_tokens_from_string
from src.utilities.parsing_utilities import parse_json

# Importing integration modules for GitLab and GitHub.

from src.integrations.github.github_committer import GitHubCommitter


class CodeCommitTool:
    """
    A tool for committing code to a source control repository.
    """

    # Mapping of source control provider names to their respective committer classes.
    source_control_to_committer_map = {
        "gitlab": None,
        "github": GitHubCommitter,
    }

    def __init__(
        self,
        configuration,
        interaction_manager: InteractionManager,
    ):
        """
        Initializes the CodeCommitTool with a given configuration and an interaction manager.

        :param configuration: Configuration settings for the tool.
        :param interaction_manager: The manager that handles interactions with language models.
        """
        self.configuration = configuration
        self.interaction_manager = interaction_manager

        # Constants for environment variables and source control providers
        self.source_control_provider = os.getenv(
            "SOURCE_CONTROL_PROVIDER", "github"
        ).lower()
        self.source_control_url = os.getenv("source_control_url")
        self.source_control_pat = os.getenv("source_control_pat")

    def commit_single_code_file(
        self,
        project_id: str,
        source_branch: str,
        target_branch: str,
        repository: str,
        commit_message: str,
        code: str,
        file_path: str,
    ):
        """
        Commits code to a source control repository.

        :param project_id: The ID of the project to commit code to, if available.
        :param source_branch: The name of the branch to use as the base for the new branch.
        :param target_branch: The name of the branch to commit code to.
        :param repository: The repository to commit code to.
        :param commit_message: The commit message.
        :param code: The code to commit.
        :param file_path: The path to the file to commit.
        """
        committer_class = self.source_control_to_committer_map[
            self.source_control_provider
        ]
        if committer_class is None:
            raise Exception(
                f"Source control provider {self.source_control_provider} is not supported."
            )

        committer = committer_class(source_control_pat=self.source_control_pat)

        code_and_file_paths = [{"code": code, "file_path": file_path}]

        try:
            committer.commit_changes(
                source_branch=source_branch,
                target_branch=target_branch,
                repository=repository,
                commit_message=commit_message,
                code_and_file_paths=code_and_file_paths,
            )
        except Exception as ex:
            return f"Failed to commit code: {ex}"

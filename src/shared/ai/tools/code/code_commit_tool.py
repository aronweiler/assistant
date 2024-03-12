import sys
import os
from typing import List

# Importing necessary modules and classes for the tool.
from langchain.base_language import BaseLanguageModel

# Adjusting system path to include the root directory for module imports.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.ai.utilities.llm_helper import get_llm
from src.integrations.github import github_issue_creator
from src.tools.code.issue_tool import IssueTool


# Importing database models and utilities.
from src.db.models.documents import Documents
from src.ai.conversations.conversation_manager import ConversationManager
from src.utilities.token_helper import num_tokens_from_string
from src.utilities.parsing_utilities import parse_json

# Importing integration modules for GitLab and GitHub.
from src.integrations.gitlab.gitlab_committer import GitlabCommitter
from src.integrations.github.github_committer import GitHubCommitter

from src.ai.tools.tool_registry import register_tool, tool_class


@tool_class
class CodeCommitTool:
    """
    A tool for committing code to a source control repository.
    """

    # Mapping of source control provider names to their respective committer classes.
    source_control_to_committer_map = {
        "gitlab": GitlabCommitter,
        "github": GitHubCommitter,
    }

    def __init__(
        self,
        configuration,
        conversation_manager: ConversationManager,
    ):
        """
        Initializes the CodeCommitTool with a given configuration and an conversation manager.

        :param configuration: Configuration settings for the tool.
        :param conversation_manager: The manager that handles interactions with language models.
        """
        self.configuration = configuration
        self.conversation_manager = conversation_manager

    @register_tool(
        display_name="Commit Code",
        help_text="Commits code to a source control repository.",
        requires_documents=False,
        description="Commits a single code file to source control.",
        additional_instructions="Call this tool when the user requests that you commit code to source control.",
        category="Code",
    )
    def commit_single_code_file(
        self,
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
        source_control_provider = self.conversation_manager.code_helper.get_provider_from_url(repository)
        
        committer_class = self.source_control_to_committer_map[
            source_control_provider.source_control_provider_name.lower()
        ]
        
        if committer_class is None:
            raise Exception(
                f"Source control provider {source_control_provider.source_control_provider_name} is not supported."
            )

        committer = committer_class(
            source_control_pat=source_control_provider.source_control_access_token,
            source_control_url=source_control_provider.source_control_provider_url,
        )

        code_and_file_paths = [{"code": code, "file_path": file_path}]

        try:
            committer.commit_changes(
                source_branch=source_branch,
                target_branch=target_branch,
                repository=repository,
                commit_message=commit_message,
                code_and_file_paths=code_and_file_paths,
            )

            return (
                f"Successfully committed code.  Details: \n\n"
                f"- Source branch: {source_branch}\n"
                f"- Target branch: {target_branch}\n"
                f"- Repository: {repository}\n"
                f"- Commit message: {commit_message}\n"
                f"- File path: {file_path}\n"
            )
        except Exception as ex:
            return f"Failed to commit code: {ex}"

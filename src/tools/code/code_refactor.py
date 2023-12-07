import sys
import os
from typing import List
import json

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
from src.integrations.gitlab.gitlab_issue_creator import GitlabIssueCreator
from src.integrations.gitlab.gitlab_issue_retriever import GitlabIssueRetriever
from src.integrations.gitlab.gitlab_retriever import GitlabRetriever

from src.integrations.github.github_issue_creator import GitHubIssueCreator
from src.integrations.github.github_retriever import GitHubRetriever


class CodeRefactorTool:
    def __init__(
        self,
        configuration,
        interaction_manager: InteractionManager,
    ):
        """
        Initializes the CodeRefactorTool with a given configuration and an interaction manager.

        :param configuration: Configuration settings for the tool.
        :param interaction_manager: The manager that handles interactions, lol.
        """
        self.configuration = configuration
        self.interaction_manager = interaction_manager

    def refactor_code_by_file_id(self, file_id: int):
        """
        Refactors code by file ID.

        :param file_id: The ID of the file to refactor.
        """

        # Get all of the code for this file_id
        code = self.get_code_by_file_id(file_id)

        # Calculate the number of tokens in the code file for size check.
        code_file_token_count = num_tokens_from_string(code)

        # Get maximum allowed token count for a code refactor based on tool configuration.
        max_token_count = self.get_max_code_refactor_token_count(
            tool_name=self.refactor_code_by_file_id.__name__
        )

        # If the file is too large, return an error message indicating so.
        if code_file_token_count > max_token_count:
            return f"File is too large to be refactored ({code_file_token_count} tokens). Adjust max code refactor tokens, or refactor this code file so that it's smaller."

        # Initialize language model for prediction.
        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.refactor_code_by_file_id.__name__,
            streaming=True,
        )

    def get_code_by_file_id(self, file_id: int):
        """
        Gets code by file ID.

        :param file_id: The ID of the file to refactor.
        """
        # Get the file_data by file ID
        code = Documents().get_file_data(file_id=file_id).decode("utf-8")

        # Return the code
        return code

    def get_max_code_refactor_token_count(self, tool_name: str) -> int:
        """
        Retrieves the maximum token count allowed for a code refactor based on tool configuration.

        :param tool_name: Name of the tool for which to retrieve the maximum token count.
        :return: The maximum number of tokens allowed in a code refactor.
        """

        # Access the max_code_size_tokens setting from the tool configuration and return its value.
        return self.configuration["tool_configurations"][tool_name][
            "additional_settings"
        ]["max_code_size_tokens"]["value"]


# Testing
if __name__ == "__main__":
    # Create the code refactor tool
    code_refactor_tool = CodeRefactorTool(configuration=None, interaction_manager=None)

    # Load the sample code review
    code_review = json.loads(
        open("src/tools/code/samples/code_review.json", "r").read()
    )

    # Refactor the code
    code_refactor_tool.refactor_code_by_file_id(file_id=644)

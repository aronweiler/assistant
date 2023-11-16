import sys
import os
import logging
import json
from typing import List

from langchain.base_language import BaseLanguageModel
from src.ai.llm_helper import get_tool_llm
from src.integrations.github import github_issue_creator

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.db.models.documents import Documents
from src.ai.interactions.interaction_manager import InteractionManager

from src.utilities.token_helper import num_tokens_from_string
from src.utilities.parsing_utilities import parse_json


from src.integrations.gitlab.gitlab_issue_creator import GitlabIssueCreator
from src.integrations.gitlab.gitlab_issue_retriever import GitlabIssueRetriever
from src.integrations.gitlab.gitlab_retriever import GitlabRetriever

from src.integrations.github.github_issue_creator import GitHubIssueCreator
from src.integrations.github.github_retriever import GitHubRetriever

class IssueTool:
    source_control_to_issue_creator_map: dict = {
        "gitlab": GitlabIssueCreator,
        "github": GitHubIssueCreator,
    }
    source_control_to_issue_retriever_map: dict = {
        "gitlab": GitlabIssueRetriever,
        "github": None,
    }
    
    def __init__(
        self,
        configuration,
        interaction_manager: InteractionManager,
    ):
        self.configuration = configuration
        self.interaction_manager = interaction_manager

    @staticmethod
    def ingest_issue_from_url(url):
        source_control_provider = os.getenv("SOURCE_CONTROL_PROVIDER", "GitHub")
        retriever = IssueTool.source_control_to_issue_retriever_map[
            source_control_provider.lower()
        ]
        if not retriever:
            return f"Source control provider {source_control_provider} does not support issue retrieval"

        retriever = retriever(
            source_control_url=os.getenv("source_control_url"),
            source_control_pat=os.getenv("source_control_pat"),
        )

        return retriever.retrieve_issue_data(url=url)

    def create_code_review_issue(
        self,
        review_data: dict,
    ):
        """
        Creates an issue containing the code review for a single reviewed file,on the source code control system specified

        # Args:
        #     source_code_file_data: A dictionary containing the project ID, file URL, file relative path, ref name, file contents
        #     review_data: A python dictionary containing the code review data to create the issue from
        """
        source_control_provider = os.getenv("SOURCE_CONTROL_PROVIDER", "GitHub")
        issue_creator = self.source_control_to_issue_creator_map[
            source_control_provider.lower()
        ]
        if not issue_creator:
            return f"Source control provider {source_control_provider} does not support issue creation"

        issue_creator = issue_creator(
            source_control_url=os.getenv("source_control_url"),
            source_control_pat=os.getenv("source_control_pat"),
        )

        result = issue_creator.generate_issue(
            review_data=review_data,
        )

        return f"Successfully created issue at {result['url']}"
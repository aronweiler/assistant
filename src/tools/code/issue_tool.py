import sys
import os
import logging
import json
from typing import List

from langchain.base_language import BaseLanguageModel
from src.ai.utilities.llm_helper import get_tool_llm
from src.ai.tools.tool_registry import register_tool, tool_class
from src.integrations.github import github_issue_creator

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.db.models.documents import Documents
from src.ai.conversations.conversation_manager import ConversationManager

from src.utilities.token_helper import num_tokens_from_string
from src.utilities.parsing_utilities import parse_json


from src.integrations.gitlab.gitlab_issue_creator import GitlabIssueCreator
from src.integrations.gitlab.gitlab_issue_retriever import GitlabIssueRetriever
from src.integrations.gitlab.gitlab_retriever import GitlabRetriever

from src.integrations.github.github_issue_creator import GitHubIssueCreator

@tool_class
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
        conversation_manager: ConversationManager,
    ):
        self.configuration = configuration
        self.conversation_manager = conversation_manager
    
    def ingest_issue_from_url(self, url):
        try:
            retriever = self.get_issue_retriever_instance(url=url)

            return retriever.retrieve_issue_data(url=url)
        except Exception as e:
            logging.error(f"Tried to get an issue from {url}.\n{e}")
            return None

    @register_tool(
        display_name="Create Issue from Code Review",
        help_text="Creates an issue on your selected provider from a Code Review",
        requires_documents=False,
        description="Creates an issue from a Code Review.",
        additional_instructions="Call this tool when the user requests an issue be created from a code review.",
    )
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

        issue_creator = self.get_issue_creator_instance(
            url=review_data['metadata']['url']
        )

        result = issue_creator.generate_issue(
            review_data=review_data,
        )

        return f"Successfully created issue at {result['url']}"


    def get_issue_creator_instance(self, url):
        source_control_provider = self.conversation_manager.code_helper.get_provider_from_url(url)
        
        if not source_control_provider:
            raise Exception(f"The URL {url} does not correspond to a configured source control provider.")
        
        supported_provider = self.conversation_manager.code_helper.get_supported_source_control_provider_by_id(source_control_provider.supported_source_control_provider_id)
        
        # Get the corresponding retriever class from the map using provider name in lowercase.
        issue_creator_class = self.source_control_to_issue_creator_map.get(
            supported_provider.name.lower()
        )
        
        # If no retriever class is found, return an error message indicating unsupported code retrieval.
        if not issue_creator_class:
            raise f"Source control provider {source_control_provider.source_control_provider_name} does not support issue creation"
        
        return issue_creator_class(
            source_control_pat=source_control_provider.source_control_access_token,
            source_control_url=source_control_provider.source_control_provider_url,
        )
        
    def get_issue_retriever_instance(self, url):
        source_control_provider = self.conversation_manager.code_helper.get_provider_from_url(url)
        
        if not source_control_provider:
            raise Exception(f"The URL {url} does not correspond to a configured source control provider.")
        
        supported_provider = self.conversation_manager.code_helper.get_supported_source_control_provider_by_id(source_control_provider.supported_source_control_provider_id)
        
        # Get the corresponding retriever class from the map using provider name in lowercase.
        issue_retriever_class = self.source_control_to_issue_retriever_map.get(
            supported_provider.name.lower()
        )
        
        # If no retriever class is found, return an error message indicating unsupported code retrieval.
        if not issue_retriever_class:
            raise f"Source control provider {source_control_provider.source_control_provider_name} does not support issue retrieval"
        
        return issue_retriever_class(
            source_control_pat=source_control_provider.source_control_access_token,
            source_control_url=source_control_provider.source_control_provider_url,
            requires_authentication=source_control_provider.requires_authentication
        )
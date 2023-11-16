import sys
import os
import logging
import json
from typing import List

from langchain.base_language import BaseLanguageModel
from src.ai.llm_helper import get_tool_llm
from src.integrations.github import github_issue_creator
from src.tools.code.issue_tool import IssueTool

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


class CodeReviewTool:
    source_control_to_retriever_map: dict = {
        "gitlab": GitlabRetriever,
        "github": GitHubRetriever,
    }
    

    def __init__(
        self,
        configuration,
        interaction_manager: InteractionManager,
    ):
        self.configuration = configuration
        self.interaction_manager = interaction_manager

        self.code_review_templates = [
            "SECURITY_CODE_REVIEW_TEMPLATE",
            "PERFORMANCE_CODE_REVIEW_TEMPLATE",
            "MEMORY_CODE_REVIEW_TEMPLATE",
            "CORRECTNESS_CODE_REVIEW_TEMPLATE",
            "MAINTAINABILITY_CODE_REVIEW_TEMPLATE",
            "RELIABILITY_CODE_REVIEW_TEMPLATE",
        ]

    def ingest_source_code_file_from_url(self, url):
        source_control_provider = os.getenv("SOURCE_CONTROL_PROVIDER", "GitHub")
        retriever = self.source_control_to_retriever_map[
            source_control_provider.lower()
        ]
        if not retriever:
            return f"Source control provider {source_control_provider} does not support file retrieval"

        retriever = retriever(
            source_control_url=os.getenv("source_control_url"),
            source_control_pat=os.getenv("source_control_pat"),
        )

        return retriever.retrieve_data(url=url)

    

    def _conduct_diff_code_review(
        self,
        diff_data,
        llm,
        additional_instructions: str = None,
        metadata: dict = None,
        existing_comments=None,
    ):
        # Add line numbers
        # code = diff_data["raw"].splitlines()
        # for line_num, line in enumerate(code):
        #     code[line_num] = f"{line_num + 1}: {line}"

        base_code_review_instructions = (
            self.interaction_manager.prompt_manager.get_prompt(
                "code_review", "BASE_CODE_REVIEW_INSTRUCTIONS_TEMPLATE"
            )
        )

        diff_code_review_format_instructions = (
            self.interaction_manager.prompt_manager.get_prompt(
                "code_review", "DIFF_CODE_REVIEW_FORMAT_TEMPLATE"
            )
        )

        base_code_review_instructions = base_code_review_instructions.format(
            format_instructions=diff_code_review_format_instructions
        )

        return self._run_code_reviews(
            code=diff_data["raw"],
            base_code_review_instructions=base_code_review_instructions,
            llm=llm,
            additional_instructions=additional_instructions,
            metadata=metadata,
        )

    def _conduct_file_code_review(
        self,
        file_data: str,
        llm,
        additional_instructions: str = None,
        metadata: dict = None,
        previous_issue=None,
    ):
        # Add line numbers
        code = file_data.splitlines()
        for line_num, line in enumerate(code):
            code[line_num] = f"{line_num + 1}: {line}"

        base_code_review_instructions = (
            self.interaction_manager.prompt_manager.get_prompt(
                "code_review", "BASE_CODE_REVIEW_INSTRUCTIONS_TEMPLATE"
            )
        )

        file_code_review_format_instructions = (
            self.interaction_manager.prompt_manager.get_prompt(
                "code_review", "FILE_CODE_REVIEW_FORMAT_TEMPLATE"
            )
        )

        base_code_review_instructions = base_code_review_instructions.format(
            format_instructions=file_code_review_format_instructions
        )

        return self._run_code_reviews(
            code=code,
            base_code_review_instructions=base_code_review_instructions,
            llm=llm,
            additional_instructions=additional_instructions,
            metadata=metadata,
        )

    def _run_code_reviews(
        self,
        code,
        base_code_review_instructions,
        llm,
        additional_instructions: str = None,
        metadata: dict = None,
    ):
        final_code_review_instructions = (
            self.interaction_manager.prompt_manager.get_prompt(
                "code_review", "FINAL_CODE_REVIEW_INSTRUCTIONS"
            ).format(
                code_summary="",
                code_dependencies="",
                code=code,
                code_metadata=metadata,
                additional_instructions=additional_instructions,
            )
        )

        review_results = {}
        comment_results = []
        for template in self.code_review_templates:
            code_review_prompt = self.interaction_manager.prompt_manager.get_prompt(
                "code_review", template
            ).format(
                base_code_review_instructions=base_code_review_instructions,
                final_code_review_instructions=final_code_review_instructions,
            )

            json_data = llm.predict(
                code_review_prompt,
                callbacks=self.interaction_manager.agent_callbacks,
            )

            data = parse_json(json_data, llm)

            comment_results.extend(data["comments"])

        review_results = {
            "language": data["language"],
            "metadata": data["metadata"],
            "comments": comment_results,
        }

        return review_results

    def conduct_code_review_from_url(
        self, target_url: str, additional_instructions: str = None
    ):
        """
        Conducts a code review for the specified file from a given target URL

        Args:
            target_url: The URL of the file to code review
        """
        if additional_instructions:
            additional_instructions = f"\nIn addition to the code review instructions, here are some additional instructions from the user that you should take into account when performing this code review:\n{additional_instructions}\n"
        else:
            additional_instructions = ""

        file_info = self.ingest_source_code_file_from_url(url=target_url)

        if file_info["type"] == "diff":
            return self._code_review_diff_from_url(
                file_info, target_url, additional_instructions
            )
        elif file_info["type"] == "file":
            return self._code_review_file_from_url(
                file_info, target_url, additional_instructions
            )
        else:
            raise Exception(
                f"Unknown file type {file_info['metadata']['type']} for {target_url}"
            )

    def _code_review_diff_from_url(
        self, metadata: dict, target_url, additional_instructions
    ):
        changes = metadata["changes"]

        # Remove changes from metadata
        metadata.pop("changes", None)

        # TODO: Add in the ability to pull any previous comments and append them to the review
        # previous_comments = self.ingest_comments_from_review(url=target_url)

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.conduct_code_review_from_url.__name__,
            streaming=True,
        )

        # Review each of the changed files
        reviews = []
        for change in changes:
            diff_metadata = {
                "review_metadata": metadata,
                "diff_metadata": {
                    "old_path": change["old_path"],
                    "new_path": change["new_path"],
                },
            }

            review = self._conduct_diff_code_review(
                diff_data=change,
                additional_instructions=additional_instructions,
                metadata=diff_metadata,
                existing_comments="",  # TBD- probably need to pull this in if we're re-reviewing a diff
                llm=llm,
            )

            reviews.append(review)

        return reviews

    def _code_review_file_from_url(
        self, file_info, target_url, additional_instructions
    ):
        file_data = file_info["file_content"]
        metadata = {
            "project_id": file_info["project_id"],
            "url": file_info["url"],
            "ref": file_info["ref"],
            "file_path": file_info["file_path"],
        }
        previous_issue = IssueTool.ingest_issue_from_url(url=target_url)

        code_file_token_count = num_tokens_from_string(file_data)
        max_token_count = self.get_max_code_review_token_count(
            self.conduct_code_review_from_url.__name__
        )
        if code_file_token_count > max_token_count:
            return f"File is too large to be code reviewed ({code_file_token_count} tokens). Adjust max code review tokens, or refactor this code file so that it's smaller."

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.conduct_code_review_from_url.__name__,
            streaming=True,
        )

        return self._conduct_file_code_review(
            file_data=file_data,
            additional_instructions=additional_instructions,
            metadata=metadata,
            previous_issue=previous_issue,
            llm=llm,
        )

    def get_max_code_review_token_count(self, tool_name: str):
        return self.configuration["tool_configurations"][tool_name][
            "additional_settings"
        ]["max_code_size_tokens"]["value"]

    def conduct_code_review_from_file_id(
        self, target_file_id: int, additional_instructions: str = None
    ):
        """
        Conducts a code review for the specified file

        Args:
            target_file_id: The id of the file to conduct a code review on
        """

        if additional_instructions:
            additional_instructions = f"\n--- ADDITIONAL INSTRUCTIONS ---\n{additional_instructions}\n--- ADDITIONAL INSTRUCTIONS ---\n"
        else:
            additional_instructions = ""

        documents = Documents()

        # Get the list of documents
        file_model = documents.get_file(
            file_id=target_file_id,
        )

        if file_model.file_classification.lower() != "code":
            return "File is not code. Please select a code file to conduct a code review on, or use a different tool."

        # Convert file data bytes to string
        file_data = documents.get_file_data(file_model.id).decode("utf-8")

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.conduct_code_review_from_file_id.__name__,
            streaming=True,
        )

        return self._conduct_file_code_review(
            file_data=file_data,
            additional_instructions=additional_instructions,
            metadata={"filename": file_model.file_name},
            llm=llm,
        )


### This stuff probably needs to make its way back into the code review chain
# dependencies = self.code_tool.get_dependency_graph(
#     target_file_id=target_file_id
# )
# dependencies = "\n----- CODE DEPENDENCIES -----\n" + dependencies + "\n----- CODE DEPENDENCIES -----\n"

# document_tool = DocumentTool(
#     configuration=self.configuration,
#     interaction_manager=self.interaction_manager,
#     llm=self.llm,
# )

# summary = document_tool.summarize_entire_document(target_file_id=target_file_id)
# summary = "\n--- CODE SUMMARY ---\n" + summary + "\n--- CODE SUMMARY ---\n"

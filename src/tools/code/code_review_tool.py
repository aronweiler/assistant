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

from src.tools.code.code_retriever_tool import CodeRetrieverTool


@tool_class
class CodeReviewTool:
    """
    A tool for conducting code reviews using different source control providers.
    It can retrieve files from URLs, conduct reviews on diffs or entire files,
    and format the results in a structured way.
    """

    def __init__(
        self,
        configuration,
        conversation_manager: ConversationManager,
    ):
        """
        Initializes the CodeReviewTool with a given configuration and an conversation manager.

        :param configuration: Configuration settings for the tool.
        :param conversation_manager: The manager that handles interactions with language models.
        """
        self.configuration = configuration
        self.conversation_manager = conversation_manager

    def get_active_code_review_templates(self, tool_name: str) -> List[dict]:
        """
        Retrieves active code review templates based on the provided tool name.

        :param tool_name: Name of the tool for which to retrieve templates.
        :return: A list of dictionaries containing template names and descriptions.
        """

        # Access additional settings specific to the tool from configuration.
        additional_settings = self.configuration["tool_configurations"][tool_name][
            "additional_settings"
        ]

        templates = []
        template_checks = {
            "security_code_review": "Security",
            "performance_code_review": "Performance",
            "memory_code_review": "Memory",
            "correctness_code_review": "Correctness",
            "maintainability_code_review": "Maintainability",
            "reliability_code_review": "Reliability",
        }

        for setting, description in template_checks.items():
            if additional_settings[f"enable_{setting}"]["value"]:
                templates.append(
                    {"name": f"{setting.upper()}_TEMPLATE", "description": description}
                )

        return templates

    def _conduct_diff_code_review(
        self,
        diff_data: dict,
        llm: BaseLanguageModel,
        additional_instructions: str = None,
        metadata: dict = None,
    ) -> dict:
        """
        Conducts a code review on a set of differences (diff) between two versions of a file.

        :param diff_data: Dictionary containing raw diff data between two file versions.
        :param llm: An instance of a language model used for generating predictions during reviews.
        :param additional_instructions: Additional instructions provided by users for this specific review task (optional).
        :param metadata: Metadata associated with this diff (optional).
        :return: A dictionary containing results of the diff code review process.
        """

        # Retrieve base code review instructions and format them with diff-specific instructions.
        base_code_review_instructions = (
            self.conversation_manager.prompt_manager.get_prompt(
                "code_review_prompts", "BASE_CODE_REVIEW_INSTRUCTIONS_TEMPLATE"
            )
        )

        diff_code_review_format_instructions = (
            self.conversation_manager.prompt_manager.get_prompt(
                "code_review_prompts", "DIFF_CODE_REVIEW_FORMAT_TEMPLATE"
            )
        )

        # Format the base instructions to include the diff-specific format instructions.
        base_code_review_instructions = base_code_review_instructions.format(
            format_instructions=diff_code_review_format_instructions
        )

        # Run the code reviews using the formatted instructions and return the results.
        return self._run_code_reviews(
            code=diff_data["raw"],
            base_code_review_instructions=base_code_review_instructions,
            llm=llm,
            tool_name=self.conduct_code_review_from_url.__name__,
            additional_instructions=additional_instructions,
            metadata=metadata,
        )

    def _conduct_file_code_review(
        self,
        file_data: str,
        llm: BaseLanguageModel,
        tool_name: str,
        additional_instructions: str = None,
        metadata: dict = None,
        previous_issue=None,
    ) -> dict:
        """
        Conducts a code review on an entire file's contents.

        :param file_data: The raw content of the file to be reviewed.
        :param llm: An instance of a language model used for generating predictions during reviews.
        :param tool_name: Name of the tool initiating this code review process.
        :param additional_instructions: Additional instructions provided by users for this specific review task (optional).
        :param metadata: Metadata associated with this file (optional).
        :return: A dictionary containing results of the file code review process.
        """

        # Split the file data into lines and prepend line numbers for clarity.
        code_with_line_numbers = [
            f"{line_num + 1}: {line}"
            for line_num, line in enumerate(file_data.splitlines())
        ]

        # Retrieve base code review instructions and format them with file-specific instructions.
        base_code_review_instructions = (
            self.conversation_manager.prompt_manager.get_prompt(
                "code_review_prompts", "BASE_CODE_REVIEW_INSTRUCTIONS_TEMPLATE"
            )
        )

        file_code_review_format_instructions = (
            self.conversation_manager.prompt_manager.get_prompt(
                "code_review_prompts", "FILE_CODE_REVIEW_FORMAT_TEMPLATE"
            )
        )

        # Format the base instructions to include the file-specific format instructions.
        base_code_review_instructions = base_code_review_instructions.format(
            format_instructions=file_code_review_format_instructions
        )

        # Run the code reviews using the formatted instructions and return the results.
        return self._run_code_reviews(
            code=code_with_line_numbers,
            base_code_review_instructions=base_code_review_instructions,
            llm=llm,
            tool_name=tool_name,
            additional_instructions=additional_instructions,
            metadata=metadata,
        )

    def _run_code_reviews(
        self,
        code: List[str],
        base_code_review_instructions: str,
        llm: BaseLanguageModel,
        tool_name: str,
        additional_instructions: str = None,
        metadata: dict = None,
    ) -> dict:
        """
        Runs code reviews using provided instructions and a language model.

        :param code: A list of strings representing the code to be reviewed.
        :param base_code_review_instructions: The base instructions for conducting the review.
        :param llm: An instance of a language model used for generating predictions during reviews.
        :param tool_name: Name of the tool initiating this code review process.
        :param additional_instructions: Additional instructions provided by users for this specific review task (optional).
        :param metadata: Metadata associated with this review (optional).
        :return: A dictionary containing results of the code review process.
        """

        # Retrieve active templates based on the tool name.
        templates = self.get_active_code_review_templates(tool_name)

        # Initialize containers for results and comments.
        review_results = {}
        comment_results = []

        if len(templates) == 0:
            # If the templates are all turned off, just use the additional instructions
            # Format final code review instructions with placeholders replaced by actual data.
            final_code_review_instructions = (
                self.conversation_manager.prompt_manager.get_prompt(
                    "code_review_prompts", "FINAL_CODE_REVIEW_INSTRUCTIONS"
                ).format(
                    code_summary="",
                    code_dependencies="",
                    code=code,
                    code_metadata=metadata,
                    additional_instructions="",
                )
            )

            if not additional_instructions or additional_instructions == "":
                code_review_prompt = (
                    self.conversation_manager.prompt_manager.get_prompt(
                        "code_review_prompts", "GENERIC_CODE_REVIEW_TEMPLATE"
                    ).format(
                        base_code_review_instructions=base_code_review_instructions,
                        final_code_review_instructions=final_code_review_instructions,
                    )
                )
            else:
                code_review_prompt = (
                    self.conversation_manager.prompt_manager.get_prompt(
                        "code_review_prompts", "CUSTOM_CODE_REVIEW_TEMPLATE"
                    ).format(
                        base_code_review_instructions=base_code_review_instructions,
                        code_review_instructions=additional_instructions,
                        final_code_review_instructions=final_code_review_instructions,
                    )
                )

            # Use language model to predict based on the formatted prompt.
            json_data = llm.predict(
                code_review_prompt,
                callbacks=self.conversation_manager.agent_callbacks,
            )

            # Parse JSON data returned by language model prediction into structured data.
            data = parse_json(json_data, llm)

            # Extend comment results with comments from current template's review.
            comment_results.extend(data["comments"])

        else:
            # Format additional instructions if provided.
            if additional_instructions:
                additional_instructions = f"\nIn addition to the base code review instructions, consider these user-provided instructions:\n{additional_instructions}\n"

            final_code_review_instructions = (
                self.conversation_manager.prompt_manager.get_prompt(
                    "code_review_prompts", "FINAL_CODE_REVIEW_INSTRUCTIONS"
                ).format(
                    code_summary="",
                    code_dependencies="",
                    code=code,
                    code_metadata=metadata,
                    additional_instructions=additional_instructions,
                )
            )

            # Iterate over each template and perform a review using the language model.
            for template in templates:
                # Get individual prompt for each type of review from the template and format it.
                code_review_prompt = (
                    self.conversation_manager.prompt_manager.get_prompt(
                        "code_review_prompts", template["name"]
                    ).format(
                        base_code_review_instructions=base_code_review_instructions,
                        final_code_review_instructions=final_code_review_instructions,
                    )
                )

                # Use language model to predict based on the formatted prompt.
                json_data = llm.predict(
                    code_review_prompt,
                    callbacks=self.conversation_manager.agent_callbacks,
                )

                # Parse JSON data returned by language model prediction into structured data.
                data = parse_json(json_data, llm)

                if "comments" in data:
                    # Extend comment results with comments from current template's review.
                    comment_results.extend(data["comments"])
                else:
                    # If no comments were returned, add a message indicating so.
                    comment_results.append(
                        {
                            "comment": f"No comments were returned for {template['description']} template.",
                            "start": None,
                            "end": None,
                            "original_code_snippet": None,
                            "suggested_code_snippet": None,
                        }
                    )

        # Sort comments based on their starting line number or addition line start if available.
        def get_start_line(comment):
            start = 1
            if "start" in comment and comment["start"] is not None:
                start = comment["start"]
            elif "add_line_start" in comment and comment["add_line_start"] is not None:
                start = comment["add_line_start"]
            elif (
                "remove_line_start" in comment
                and comment["remove_line_start"] is not None
            ):
                start = comment["remove_line_start"]

            return start

        comment_results.sort(key=lambda k: get_start_line(k))

        # Extract metadata from the last set of data processed (assumes consistent structure across all templates).
        review_metadata = data["metadata"]

        # Add information about which reviews were performed to metadata.
        review_metadata["reviews_performed"] = [
            template["description"] for template in templates
        ]

        # Compile final review results including language, metadata, and comments.
        review_results = {
            "language": data["language"],
            "metadata": review_metadata,
            "comments": comment_results,
        }

        if self.is_output_json(tool_name):
            # Return formatted review results as a JSON string enclosed in triple backticks for markdown formatting.
            return f"```json\n{review_results}\n```"
        else:
            return self.format_review_results(review_results)

    @register_tool(
        display_name="Conduct Code Review from URL",
        help_text="Conducts a code review on a URL",
        requires_documents=False,
        description="Performs a code review of a specified code file.",
        additional_instructions="Use this tool for conducting a code review on a URL. Make sure to extract and pass the URL specified by the user as an argument to this tool.  Use the additional_instructions field to pass any code review additional instructions from the user, if any.",
    )
    def conduct_code_review_from_url(
        self, target_url: str, additional_instructions: str = None
    ) -> str:
        """
        Conducts a code review on a file or diff obtained from a given URL.

        :param target_url: The URL of the source code to be reviewed.
        :param additional_instructions: Additional instructions provided by users for this specific review task (optional).
        :return: A string containing the formatted results of the code review in JSON.
        """

        # Retrieve file information from the URL.
        retriever = CodeRetrieverTool()
        file_info = retriever.retrieve_source_code_from_url(url=target_url)

        # Initialize an empty string to hold the review results.
        review = ""

        # Determine the type of file and conduct appropriate type of review.
        if file_info["type"] == "diff":
            review = self._review_diff_from_url(
                file_info, target_url, additional_instructions
            )
        elif file_info["type"] == "file":
            review = self._review_file_from_url(
                file_info, target_url, additional_instructions
            )
        else:
            raise Exception(
                f"Unknown file type {file_info['metadata']['type']} for {target_url}"
            )

        return review

    def _review_diff_from_url(
        self, metadata: dict, target_url: str, additional_instructions: str
    ) -> List[dict]:
        """
        Conducts a code review on a diff from a URL and returns structured results.

        :param metadata: Metadata associated with the diff.
        :param target_url: The URL of the source code to be reviewed.
        :param additional_instructions: Additional instructions provided by users for this specific review task (optional).
        :return: A list of dictionaries containing the results of the diff code reviews.
        """

        # Extract changes from metadata and remove 'changes' key from metadata.
        changes = metadata.pop("changes", None)

        # Initialize language model for prediction.
        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.conduct_code_review_from_url.__name__,
            streaming=True,
        )

        # Initialize an empty list to hold individual change reviews.
        reviews = []
        metadata["changes"] = []

        # Iterate over each change in the diff and conduct a review.
        for change in changes:
            # Prepare metadata specific to this change within the diff.
            metadata["changes"].append(
                {
                    "old_path": change["old_path"],
                    "new_path": change["new_path"],
                }
            )

            # Conduct a review on this particular change and add it to the list of reviews.
            review = self._conduct_diff_code_review(
                diff_data=change,
                additional_instructions=additional_instructions,
                metadata=metadata,
                llm=llm,
            )

            reviews.append(review)

        return reviews

    def _review_file_from_url(
        self, file_info: dict, target_url: str, additional_instructions: str
    ) -> dict:
        """
        Conducts a code review on a single file from a URL and returns structured results.

        :param file_info: Metadata and content information about the file.
        :param target_url: The URL of the source code to be reviewed.
        :param additional_instructions: Additional instructions provided by users for this specific review task (optional).
        :return: A dictionary containing the results of the file code review.
        """

        # Extract file content from file_info and remove 'file_content' key.
        file_data = file_info.pop("file_content", None)

        # Retrieve any existing issues related to this file from its URL.
        issue_tool = IssueTool(self.configuration, self.conversation_manager)
        previous_issue = issue_tool.ingest_issue_from_url(url=target_url)

        # Calculate the number of tokens in the code file for size check.
        code_file_token_count = num_tokens_from_string(file_data)

        # Get maximum allowed token count for a code review based on tool configuration.
        max_token_count = self.get_max_code_review_token_count(
            self.conduct_code_review_from_url.__name__
        )

        # If the file is too large, return an error message indicating so.
        if code_file_token_count > max_token_count:
            return f"File is too large to be code reviewed ({code_file_token_count} tokens). Adjust max code review tokens, or refactor this code file so that it's smaller."

        # Initialize language model for prediction.
        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.conduct_code_review_from_url.__name__,
            streaming=True,
        )

        # Conduct a review on the entire file content and return the results.
        return self._conduct_file_code_review(
            file_data=file_data,
            additional_instructions=additional_instructions,
            metadata=file_info,
            previous_issue=previous_issue,
            llm=llm,
            tool_name=self.conduct_code_review_from_url.__name__,
        )

    def get_max_code_review_token_count(self, tool_name: str) -> int:
        """
        Retrieves the maximum token count allowed for a code review based on tool configuration.

        :param tool_name: Name of the tool for which to retrieve the maximum token count.
        :return: The maximum number of tokens allowed in a code review.
        """

        # Access the max_code_size_tokens setting from the tool configuration and return its value.
        return self.configuration["tool_configurations"][tool_name][
            "additional_settings"
        ]["max_code_size_tokens"]["value"]

    @register_tool(
        display_name="Conduct Code Review from Loaded File",
        help_text="Conducts a code review on a loaded code file",
        requires_documents=True,
        description="Performs a code review of a specified code file.",
        additional_instructions="Use this tool for conducting a code review on a loaded code file.  Use the additional_instructions field to pass any code review additional instructions from the user, if any.",
    )
    def conduct_code_review_from_file_id(
        self, target_file_id: int, additional_instructions: str = None
    ) -> dict:
        """
        Conducts a code review on a file identified by its database ID.

        :param target_file_id: The database ID of the file to be reviewed.
        :param additional_instructions: Additional instructions provided by users for this specific review task (optional).
        :return: A dictionary containing the results of the code review.
        """

        # Retrieve file model from database using Documents class and file ID.
        documents = Documents()
        file_model = documents.get_file(file_id=target_file_id)

        # Check if the retrieved file is classified as code; if not, return an error message.
        if file_model.file_classification.lower() != "code":
            return "File is not code. Please select a code file to conduct a review on, or use a different tool."

        # Get raw file data from database and decode it.
        file_data = documents.get_file_data(file_model.id).decode("utf-8")

        # Initialize language model for prediction.
        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.conduct_code_review_from_file_id.__name__,
            streaming=True,
        )

        # Conduct a review on the entire file content and return the results.
        return self._conduct_file_code_review(
            file_data=file_data,
            additional_instructions=additional_instructions,
            metadata={"filename": file_model.file_name},
            llm=llm,
            tool_name=self.conduct_code_review_from_file_id.__name__,
        )

    def is_output_json(self, tool_name: str) -> int:
        """
        Retrieves the setting for whether or not to output JSON based on tool configuration.
        """

        # Access the max_code_size_tokens setting from the tool configuration and return its value.
        return self.configuration["tool_configurations"][tool_name][
            "additional_settings"
        ]["json_output"]["value"]

    def format_review_results(self, review_results: dict) -> str:
        """
        Formats the results of a code review into a string.

        :param review_results: The results of a code review.
        :return: A string containing the formatted results of the code review.
        """
        formatted_results = """## Code Review
- Language: **{language}**
- File: **{filename_or_url}**

{comments}
"""
        comments = ""
        for comment in review_results["comments"]:
            start = 1
            end = 1
            if "start" in comment:
                start = comment["start"]
                end = comment["end"]
            elif "add_line_start" in comment:
                start = comment["add_line_start"]
                end = comment["add_line_end"]
            elif "remove_line_start" in comment:
                start = comment["remove_line_start"]
                end = comment["remove_line_end"]

            if "url" in review_results["metadata"]:
                comments += f" [Line {start} to {end}]({review_results['metadata']['url']}#L{start}-L{end})\n\n"
            else:
                comments += f"Line {start} to {end}\n\n"

            if (
                "original_code_snippet" in comment
                and comment["original_code_snippet"] is not None
                and comment["original_code_snippet"].strip() != ""
            ):
                comments += "##### Original code:\n"
                comments += f"```{review_results['language']}\n"
                comments += comment["original_code_snippet"] + "\n"
                comments += "```\n\n"

            comments += f"\n{comment['comment']}\n"

            if (
                "suggested_code_snippet" in comment
                and comment["suggested_code_snippet"] is not None
                and comment["suggested_code_snippet"].strip() != ""
                and comment["suggested_code_snippet"]
                != comment["original_code_snippet"]
            ):
                comments += "\n##### Suggested change:\n"
                comments += f"```{review_results['language']}\n"
                comments += comment["suggested_code_snippet"] + "\n"
                comments += "```\n\n"

        formatted_results = formatted_results.format(
            language=review_results["language"],
            filename_or_url=review_results["metadata"]["url"]
            if "url" in review_results["metadata"]
            else review_results["metadata"]["filename"],
            comments=comments,
        )

        # Return the formatted results.
        return formatted_results

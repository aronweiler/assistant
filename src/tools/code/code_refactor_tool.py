import sys
import os
from typing import List

# Importing necessary modules and classes for the tool.
from langchain.base_language import BaseLanguageModel
from src.ai.prompts.prompt_models.code_refactor import (
    CodeRefactorInput,
    CodeRefactorOutput,
)
from src.ai.prompts.query_helper import QueryHelper
from src.ai.tools.tool_registry import register_tool, tool_class

from src.tools.code.code_retriever_tool import CodeRetrieverTool

# Adjusting system path to include the root directory for module imports.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.ai.utilities.llm_helper import get_tool_llm
from src.integrations.github import github_issue_creator
from src.tools.code.issue_tool import IssueTool


# Importing database models and utilities.
from src.db.models.documents import Documents
from src.ai.conversations.conversation_manager import ConversationManager
from src.utilities.token_helper import num_tokens_from_string
from src.utilities.parsing_utilities import parse_json


@tool_class
class CodeRefactorTool:
    """
    A tool for conducting code refactors using different source control providers.
    It can retrieve files from URLs or files from the database, conduct refactors on those files,
    and format the results in a structured way.
    """

    def __init__(
        self,
        configuration,
        conversation_manager: ConversationManager,
    ):
        """
        Initializes the CodeRefactorTool with a given configuration and an conversation manager.

        :param configuration: Configuration settings for the tool.
        :param conversation_manager: The manager that handles interactions with language models.
        """
        self.configuration = configuration
        self.conversation_manager = conversation_manager

    def get_active_code_refactor_templates(self, tool_name: str) -> List[dict]:
        """
        Retrieves active code refactor templates based on the provided tool name.

        :param tool_name: Name of the tool for which to retrieve templates.
        :return: A list of dictionaries containing template names and descriptions.
        """

        # Access additional settings specific to the tool from configuration.
        additional_settings = self.configuration["tool_configurations"][tool_name][
            "additional_settings"
        ]

        templates = []
        template_checks = {
            "enable_code_security_examination": "Security",
            "enable_code_performance_examination": "Performance",
            "enable_code_memory_examination": "Memory",
            "enable_code_correctness_examination": "Correctness",
            "enable_code_maintainability_examination": "Maintainability",
            "enable_code_reliability_examination": "Reliability",
        }

        for setting, description in template_checks.items():
            if additional_settings[f"{setting}"]["value"]:
                templates.append(
                    {"name": f"{setting.lstrip('enable_').upper()}_TEMPLATE", "description": description}
                )

        return templates

    def _conduct_code_refactor(
        self,
        code: str,
        llm: BaseLanguageModel,
        tool_name: str,
        additional_instructions: str = None,
        metadata: dict = None,
    ) -> dict:
        """
        Conducts a refactor on a file.
        """

        # Retrieve active templates based on the tool name.
        templates = self.get_active_code_refactor_templates(tool_name)

        # Initialize containers for results
        refactor_results = []

        if (
            len(templates) == 0
            and not additional_instructions
            or additional_instructions.strip() == ""
        ):
            # If the templates are all turned off, just use the additional instructions
            # If there are no additional instructions, don't perform a refactor, throw an exception
            raise Exception(
                "No refactor templates are enabled and no additional instructions were provided"
            )

        code = self._process_templates(
            templates=templates,
            refactor_results=refactor_results,
            metadata=metadata,
            additional_instructions=additional_instructions,
            code=code,
            llm=llm,
        )

        # Extract metadata from the last set of data processed (assumes consistent structure across all templates).
        refactor_metadata = refactor_results[0]["metadata"]

        # Compile final refactor results including language, metadata, and comments.
        results = {
            "language": refactor_results[0]["language"],
            "metadata": refactor_metadata,
            "refactor_thoughts": [
                {
                    "refactor_type": refactor["refactor_type"],
                    "thoughts": refactor["thoughts"],
                }
                for refactor in refactor_results
            ],
            "refactored_code": code,
        }

        if self.is_output_json(tool_name):
            # Return formatted refactor results as a JSON string enclosed in triple backticks for markdown formatting.
            return f"```json\n{results}\n```"
        else:
            return self.format_refactor_results(results)

    def _process_templates(
        self,
        refactor_results,
        templates,
        metadata: dict,
        additional_instructions: str,
        code: str,
        llm: BaseLanguageModel,
    ):
        if not templates or len(templates) == 0:
            # process the additional instructions on their own
            code, data = self._perform_single_refactor(
                metadata=metadata,
                code=code,
                llm=llm,
                additional_instructions=additional_instructions,                
            )

        else:
            # Iterate over each template and perform a refactor using the language model.
            for template in templates:
                template_instructions = self.conversation_manager.prompt_manager.get_prompt_by_template_name(
                    template["name"]
                )

                code, data = self._perform_single_refactor(
                    metadata=metadata,
                    code=code,
                    llm=llm,
                    template=template,
                    template_instructions=template_instructions,
                    additional_instructions=additional_instructions,
                )

                # Append results from current template's refactor.
                # Note: This is not currently used anywhere- the ultimate result of this tool is just the final code
                # However, this is here so that we can do something with the data generated by each of the steps in the future.
                refactor_results.append(data)

            return code

    def _perform_single_refactor(
        self,
        metadata,
        code,
        llm,
        template="User Instructions",
        template_instructions="",
        additional_instructions="",
    ):
        input_object = CodeRefactorInput(
            code_refactor_instructions=template_instructions,
            additional_instructions=additional_instructions,
            code_metadata=metadata,
            code=code,
        )

        query_helper = QueryHelper(self.conversation_manager.prompt_manager)

        result: CodeRefactorOutput = query_helper.query_llm(
            llm=llm,
            input_class_instance=input_object,
            prompt_template_name="CODE_REFACTOR_INSTRUCTIONS_TEMPLATE",
            output_class_type=CodeRefactorOutput,
        )

        # Feed the results of the refactor into the next refactor by setting the code to the refactored code
        # (so the AI doesn't continue to refactor the same original code)
        code = result.refactored_code

        # Create a new dictionary containing the refactor type and thoughts.
        data = {
            "refactor_type": template["description"],
            "thoughts": result.thoughts,
            "refactored_code": result.refactored_code,
            "metadata": result.metadata,
            "language": result.language,
        }

        return code, data

    @register_tool(
        display_name="Perform a Code Refactor on a URL",
        requires_documents=False,
        help_text="Performs a code refactor of a specified URL.",
        description="Performs a code refactor of a specified URL.",
        additional_instructions="Use this tool for conducting a code refactor on a URL. Make sure to extract and pass the URL specified by the user as an argument to this tool.  Use the additional_instructions field to pass any code refactor additional instructions from the user, if any.",
    )
    def conduct_code_refactor_from_url(
        self, target_url: str, additional_instructions: str = None
    ) -> str:
        """
        Conducts a code refactor on a file or diff obtained from a given URL.

        :param target_url: The URL of the source code to be refactored.
        :param additional_instructions: Additional instructions provided by users for this specific refactor task (optional).
        :return: A string containing the formatted results of the code refactor in JSON.
        """

        # Retrieve file information from the URL.
        retriever = CodeRetrieverTool()
        file_info = retriever.retrieve_source_code_from_url(url=target_url)

        # Determine the type of file and conduct appropriate type of refactor.
        return self._refactor_file_from_url(
            file_info, target_url, additional_instructions
        )

    def _refactor_file_from_url(
        self, file_info: dict, target_url: str, additional_instructions: str
    ) -> dict:
        """
        Conducts a code refactor on a single file from a URL and returns structured results.

        :param file_info: Metadata and content information about the file.
        :param target_url: The URL of the source code to be refactored.
        :param additional_instructions: Additional instructions provided by users for this specific refactor task (optional).
        :return: A dictionary containing the results of the file code refactor.
        """

        # Extract file content from file_info and remove 'file_content' key.
        code = file_info.pop("file_content", None)

        # Calculate the number of tokens in the code file for size check.
        code_file_token_count = num_tokens_from_string(code)

        # Get maximum allowed token count for a code refactor based on tool configuration.
        max_token_count = self.get_max_code_refactor_token_count(
            self.conduct_code_refactor_from_url.__name__
        )

        # If the file is too large, return an error message indicating so.
        if code_file_token_count > max_token_count:
            return f"File is too large to be refactored ({code_file_token_count} tokens). Adjust max code refactor tokens, or refactor this code file so that it's smaller."

        # Initialize language model for prediction.
        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.conduct_code_refactor_from_url.__name__,
            streaming=True,
            callbacks=self.conversation_manager.agent_callbacks,
        )

        # Conduct a refactor on the entire file content and return the results.
        return self._conduct_code_refactor(
            code=code,
            additional_instructions=additional_instructions,
            metadata=file_info,
            llm=llm,
            tool_name=self.conduct_code_refactor_from_url.__name__,
        )

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

    def is_output_json(self, tool_name: str) -> int:
        """
        Retrieves the setting for whether or not to output JSON based on tool configuration.
        """

        # Access the max_code_size_tokens setting from the tool configuration and return its value.
        return self.configuration["tool_configurations"][tool_name][
            "additional_settings"
        ]["json_output"]["value"]

    @register_tool(
        display_name="Perform a Code Refactor on Loaded Code File",
        help_text="Performs a code refactor of a specified code file.",
        requires_documents=False,
        description="Performs a code refactor of a specified code file.",
        additional_instructions="Use this tool for conducting a code refactor on a URL. Make sure to extract and pass the URL specified by the user as an argument to this tool.  Use the additional_instructions field to pass any code refactor additional instructions from the user, if any.",
    )
    def conduct_code_refactor_from_file_id(
        self, target_file_id: int, additional_instructions: str = None
    ) -> dict:
        """
        Conducts a code refactor on a file identified by its database ID.

        :param target_file_id: The database ID of the file to be refactored.
        :param additional_instructions: Additional instructions provided by users for this specific refactor task (optional).
        :return: A dictionary containing the results of the code refactor.
        """

        # Format additional instructions if provided.
        if additional_instructions:
            additional_instructions = f"\n--- ADDITIONAL INSTRUCTIONS ---\n{additional_instructions}\n--- ADDITIONAL INSTRUCTIONS ---\n"

        # Retrieve file model from database using Documents class and file ID.
        documents = Documents()
        file_model = documents.get_file(file_id=target_file_id)

        # Check if the retrieved file is classified as code; if not, return an error message.
        if file_model.file_classification.lower() != "code":
            return "File is not code. Please select a code file to conduct a refactor on, or use a different tool."

        # Get raw file data from database and decode it.
        code = documents.get_file_data(file_model.id).decode("utf-8")

        # Initialize language model for prediction.
        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.conduct_code_refactor_from_file_id.__name__,
            streaming=True,
            ## callbacks=self.conversation_manager.agent_callbacks,
        )

        # Conduct a refactor on the entire file content and return the results.
        return self._conduct_code_refactor(
            code=code,
            additional_instructions=additional_instructions,
            metadata={"filename": file_model.file_name},
            llm=llm,
            tool_name=self.conduct_code_refactor_from_file_id.__name__,
        )

    def format_refactor_results(self, refactor_results: dict) -> str:
        """
        Formats the results of a code refactor into a string.

        :param refactor_results: The results of a code refactor.
        :return: A string containing the formatted results of the code refactor.
        """
        formatted_results = """## Code Refactor
- Language: **{language}**
- File: **{filename_or_url}**

{thoughts}

### Refactored Code
```{language}
{code}
```
"""

        thoughts = "\n\n".join(
            [
                f"#### {thought['refactor_type']}\n- {thought['thoughts']}"
                for thought in refactor_results["refactor_thoughts"]
            ]
        )

        formatted_results = formatted_results.format(
            language=refactor_results["language"],
            filename_or_url=refactor_results["metadata"]["url"]
            if "url" in refactor_results["metadata"]
            else refactor_results["metadata"]["filename"],
            thoughts=thoughts,
            code=refactor_results["refactored_code"],
        )

        # Return the formatted results.
        return formatted_results



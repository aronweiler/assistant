from typing import List

import json

from langchain.chains.llm import LLMChain
from langchain.base_language import BaseLanguageModel
from langchain.chains import (
    RetrievalQAWithSourcesChain,
    StuffDocumentsChain,
    ReduceDocumentsChain,
)
from langchain.schema import Document
from langchain.chains.summarize import load_summarize_chain
from src.ai.tools.tool_registry import register_tool, tool_class
from src.db.models.domain.code_file_model import CodeFileModel
from src.utilities.parsing_utilities import parse_json

from src.utilities.token_helper import num_tokens_from_string

from src.db.models.conversation_messages import SearchType
from src.db.models.documents import Documents
from src.db.models.pgvector_retriever import PGVectorRetriever

from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.llm_helper import get_tool_llm
import src.utilities.configuration_utilities as configuration_utilities


@tool_class
class CodeRepositoryTool:
    def __init__(
        self,
        configuration,
        conversation_manager: ConversationManager,
    ):
        self.configuration = configuration
        self.conversation_manager = conversation_manager

    @register_tool(
        display_name="File Name Search",
        requires_repository=True,
        description="Search for files by providing a partial or full file name.",
        additional_instructions="Input a partial or complete file name to receive a list of matching files from the repository. Include a summary by setting `include_summary` to `true` if you need help identifying the correct file.",
    )
    def file_name_search(self, partial_file_name: str, include_summary: bool = False):
        """Looks up a file in the repository by partial file name."""
        code_files = (
            self.conversation_manager.code_helper.get_code_files_by_partial_name(
                repository_id=self.conversation_manager.get_selected_repository().id,
                partial_file_name=partial_file_name,
            )
        )

        results = ""
        for code_file in code_files:
            results += f"**\n{code_file.code_file_name} (ID: {code_file.id})\n**"
            if include_summary:
                results += f"Summary: {code_file.code_file_summary}\n"

        return results

    @register_tool(
        display_name="Repository Structure Overview",
        requires_repository=True,
        description="Obtain a hierarchical list of all files and directories within the repository.",
        additional_instructions="Retrieve a structured list of the repository's contents. For detailed file summaries, set `include_summary` to `true`, but be aware this may increase processing time.",
    )
    def repository_structure_overview(self, include_summary: bool = False):
        """Gets the list of files and directories in a loaded code repository."""

        code_files = self.conversation_manager.code_helper.get_code_files(
            repository_id=self.conversation_manager.get_selected_repository().id
        )

        result = ""
        for code_file in code_files:
            result += f"**\n{code_file.code_file_name}\n**"
            if include_summary:
                result += f"Summary: {code_file.code_file_summary}\n"

        return result

    @register_tool(
        display_name="Codebase Analysis",
        requires_repository=True,
        description="Generate metrics summarizing the repository's codebase, such as file counts and lines of code.",
        additional_instructions="This tool provides an overview of the repository's size and composition, including the total number of files, lines of code, and a file type distribution.",
    )
    def codebase_analysis(self):
        """Generates a summary of the entire codebase in a loaded repository."""
        code_files = self.conversation_manager.code_helper.get_code_files(
            repository_id=self.conversation_manager.get_selected_repository().id
        )

        file_count = len(code_files)
        total_lines = 0
        file_type_breakdown = {}

        for code_file in code_files:
            # Count lines of code
            lines = code_file.code_file_content.count("\n") + 1
            total_lines += lines

            # Breakdown by file type
            file_extension = code_file.code_file_name.split(".")[-1]
            if file_extension not in file_type_breakdown:
                file_type_breakdown[file_extension] = {"count": 0, "lines": 0}
            file_type_breakdown[file_extension]["count"] += 1
            file_type_breakdown[file_extension]["lines"] += lines

        # Generate summary report
        summary = f"Codebase Summary:\n"
        summary += f"Total number of files: {file_count}\n"
        summary += f"Total lines of code: {total_lines}\n"
        summary += "Breakdown by file type:\n"
        for file_type, stats in file_type_breakdown.items():
            summary += (
                f"  * .{file_type}: {stats['count']} files, {stats['lines']} lines\n"
            )

        return summary

    @register_tool(
        display_name="Specific File Retrieval",
        requires_repository=True,
        description="Retrieve a particular file from the repository using its unique identifier.",
        additional_instructions="To fetch a specific file, supply its ID. Use the 'Repository Structure Overview' tool to find necessary file identifiers.",
    )
    def specific_file_retrieval(self, file_id: int):
        """Gets a specific code file from a loaded code repository by name or ID."""
        if file_id is not None:
            # Get the code file by ID
            code_file = self.conversation_manager.code_helper.get_code_file_by_id(
                file_id
            )
        else:
            return "Please provide a file ID.  File IDs can be found by using the repository structure overview tool."

        if code_file is None:
            return "Code file not found."

        return {
            "file_name": code_file.code_file_name,
            "file_content": code_file.code_file_content,
        }

    @register_tool(
        display_name="Retrieve Code Files by Folder",
        description="Retrieves all code files from the database that reside in a specified folder.",
        additional_instructions=None,
        requires_repository=True,
    )
    def get_code_files_by_folder(
        self, repository_id: int, folder_path: str, include_summary: bool
    ) -> List[CodeFileModel]:
        """Retrieves all code files from the database that reside in a specified folder."""
        try:
            code_files = self.conversation_manager.code_helper.get_code_files_by_folder(
                repository_id=repository_id, folder_path=folder_path
            )

            if code_files is None or len(code_files) == 0:
                return "No code files found in the specified folder."

            # Extract the required information from the search results
            file_info_list = [
                {
                    "file_id": result.id,
                    "file_name": result.code_file_name,
                    "file_summary": result.code_file_summary
                    if include_summary
                    else None,
                }
                for result in code_files
            ]

            # Return the list of file information
            return file_info_list
        except Exception as e:
            return f"An error occurred during the search: {str(e)}"

    @register_tool(
        display_name="Function Presence Check",
        requires_repository=True,
        description="Identify files containing specified functions by their names.",
        additional_instructions="List the names of functions to locate files that contain them. This tool returns file IDs and names, which can be used to retrieve the full file content.",
    )
    def function_presence_check(self, partial_function_names: List[str]):
        """Locate Files Containing a Particular Function or Functions"""
        try:
            # Use the file_information_discovery tool to find files that may contain the desired functionality
            file_info_list = self.file_information_discovery(
                semantic_similarity_query="",
                keywords_list=partial_function_names,
            )

            return file_info_list
        except Exception as e:
            return f"An error occurred during the search: {str(e)}"

    @register_tool(
        display_name="Codebase Functionality Search",
        requires_repository=True,
        description="Find code snippets related to a described functionality within the repository.",
        additional_instructions="Describe the functionality or provide keywords to locate relevant code snippets across the repository. Results include file names, IDs, and extracted code segments.",
    )
    def codebase_functionality_search(self, description: str, keywords_list: List[str]):
        """Locates specific functionality within the codebase."""
        try:
            # Use the file_information_discovery tool to find files that may contain the desired functionality
            file_info_list = self.file_information_discovery(
                semantic_similarity_query=description, keywords_list=keywords_list
            )

            # Process the results to extract relevant code snippets
            functionality_snippets = []
            for file_info in file_info_list:
                code_file = self.specific_file_retrieval(file_id=file_info["file_id"])

                get_relevant_snippets_prompt = (
                    self.conversation_manager.prompt_manager.get_prompt(
                        "code_general", "GET_RELEVANT_SNIPPETS_TEMPLATE"
                    )
                ).format(
                    file_id=file_info["file_id"],
                    file_name=file_info["file_name"],
                    code=code_file["file_content"],
                    description=description,
                )

                llm = get_tool_llm(
                    configuration=self.configuration,
                    func_name=self.codebase_functionality_search.__name__,
                    streaming=True,
                )

                relevant_snippets = parse_json(
                    llm.predict(
                        get_relevant_snippets_prompt,
                        callbacks=self.conversation_manager.agent_callbacks,
                    ),
                    llm=llm,
                )

                if isinstance(relevant_snippets, str):
                    relevant_snippets = [relevant_snippets]

                if len(relevant_snippets) == 0:
                    relevant_snippets = [
                        f"No relevant snippets found in {file_info['file_name']}."
                    ]

                functionality_snippets.append(
                    {
                        "file_name": file_info["file_name"],
                        "file_id": file_info["file_id"],
                        "snippets": relevant_snippets,  # Replace with actual snippets extracted from 'file_content'
                    }
                )

            return functionality_snippets
        except Exception as e:
            return f"An error occurred during the search: {str(e)}"

    @register_tool(
        display_name="File Information Discovery",
        requires_repository=True,
        description="Search the repository for files based on a query and keywords, returning concise file information.",
        additional_instructions="Use a combination of a semantic query and keywords to search for files. This tool returns file IDs, names, and summaries, suitable for obtaining an overview without full file contents.",
    )
    def file_information_discovery(
        self, semantic_similarity_query: str, keywords_list: List[str]
    ):
        """Searches the loaded repository for the given query and returns file IDs, names, and summaries."""
        try:
            # Perform the search using the existing _search_repository_documents method
            code_file_model_search_results: List[
                CodeFileModel
            ] = self.conversation_manager.code_helper.search_code_files(
                repository_id=self.conversation_manager.get_selected_repository().id,
                similarity_query=semantic_similarity_query,
                keywords=keywords_list,
                top_k=self.conversation_manager.tool_kwargs.get("search_top_k", 5),
            )

            # Extract the required information from the search results
            file_info_list = [
                {
                    "file_id": result.id,
                    "file_name": result.code_file_name,
                    "file_summary": result.code_file_summary,
                }
                for result in code_file_model_search_results
            ]

            # Return the list of file information
            return file_info_list
        except Exception as e:
            return f"An error occurred during the search: {str(e)}"

    @register_tool(
        display_name="Comprehensive Repository Search",
        requires_repository=True,
        description="Conduct an extensive search of the repository to return complete file contents related to a query.",
        additional_instructions="Perform a detailed search using a semantic query and keywords. This tool returns the full content of matching files but is limited by size constraints and should not be used for exhaustive file listings.",
    )
    def comprehensive_repository_search(
        self,
        semantic_similarity_query: str,
        keywords_list: List[str],
        user_query: str,
    ):
        """Searches the loaded repository for the given query."""

        try:
            # Get the split prompt settings
            split_prompt_settings = self.configuration["tool_configurations"][
                self.comprehensive_repository_search.__name__
            ]["additional_settings"]["split_prompt"]

            split_prompts = split_prompt_settings["value"]

            # If there are more than 0 additional prompts, we need to create them
            if split_prompts > 1:
                llm = get_tool_llm(
                    configuration=self.configuration,
                    func_name=self.search_loaded_repository.__name__,
                    streaming=True,
                    # Crank up the frequency and presence penalties to make the LLM give us more variety
                    model_kwargs={
                        "frequency_penalty": 0.7,
                        "presence_penalty": 0.9,
                    },
                )

                additional_prompt_prompt = (
                    self.conversation_manager.prompt_manager.get_prompt(
                        "prompt_refactoring", "ADDITIONAL_PROMPTS_TEMPLATE"
                    )
                )

                def get_chat_history():
                    if self.conversation_manager:
                        return (
                            self.conversation_manager.conversation_token_buffer_memory.buffer_as_str
                        )
                    else:
                        return "No chat history."

                split_prompts = llm.predict(
                    additional_prompt_prompt.format(
                        additional_prompts=split_prompts,
                        user_query=user_query,
                        chat_history=get_chat_history(),
                    ),
                    callbacks=self.conversation_manager.agent_callbacks,
                )

                split_prompts = parse_json(split_prompts, llm)

                results = []
                for prompt in split_prompts["prompts"]:
                    results.append(
                        self._search_repository_documents(
                            semantic_similarity_query=prompt[
                                "semantic_similarity_query"
                            ],
                            keywords_list=prompt["keywords_list"],
                            user_query=prompt["query"],
                        )
                    )

                return "\n".join(results)
        except:
            pass

        return self._search_repository_documents(
            repository_id=self.conversation_manager.get_selected_repository().id,
            semantic_similarity_query=semantic_similarity_query,
            keywords_list=keywords_list,
            user_query=user_query,
        )

    def _search_repository_documents(
        self,
        repository_id: int,
        semantic_similarity_query: str,
        keywords_list: List[str],
        user_query: str,
    ):
        code_file_model_search_results: List[
            CodeFileModel
        ] = self.conversation_manager.code_helper.search_code_files(
            repository_id=repository_id,
            similarity_query=semantic_similarity_query,
            keywords=keywords_list,
            top_k=self.conversation_manager.tool_kwargs.get("search_top_k", 5),
        )

        identify_likely_files_prompt = (
            self.conversation_manager.prompt_manager.get_prompt(
                "code_general", "IDENTIFY_LIKELY_FILES_TEMPLATE"
            )
        )

        summaries = ""
        for result in code_file_model_search_results:
            # Get the code file keywords, and descriptions
            keywords = self.conversation_manager.code_helper.get_code_file_keywords(
                result.id
            )
            descriptions = (
                self.conversation_manager.code_helper.get_code_file_descriptions(
                    result.id
                )
            )

            summaries += f"\n### (ID: {result.id}) {result.code_file_name}\n**Summary:** {result.code_file_summary}\n**Keywords:** {', '.join(keywords)}\n**Descriptions:** {', '.join(descriptions)}\n\n"

        identify_likely_files_prompt = identify_likely_files_prompt.format(
            summaries=summaries,
            user_query=user_query,
        )

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.search_loaded_repository.__name__,
            streaming=True,
        )

        result = llm.predict(
            identify_likely_files_prompt,
            callbacks=self.conversation_manager.agent_callbacks,
        )

        # Now we have the result of which file(s) the AI thinks are most likely to contain the code that we're looking for
        likely_file_ids = parse_json(result, llm)

        code_contents = []
        for file_id in likely_file_ids:
            code_file: CodeFileModel = (
                self.conversation_manager.code_helper.get_code_file_by_id(file_id)
            )
            code_contents.append(
                {
                    "file": code_file.code_file_name,
                    "content": code_file.code_file_content,
                }
            )

        # Now we have the code contents, we can run it through the LLM to try to answer the question
        answer_query_prompt = self.conversation_manager.prompt_manager.get_prompt(
            "code_general", "ANSWER_QUERY_TEMPLATE"
        )

        code_contents_string = ""
        for code_content in code_contents:
            code_contents_string += (
                f"**{code_content['file']}:**\n```\n{code_content['content']}\n```\n\n"
            )

        answer_query_prompt = answer_query_prompt.format(
            code_contents=code_contents_string,
            user_query=user_query,
        )

        answer = llm.predict(
            answer_query_prompt, callbacks=self.conversation_manager.agent_callbacks
        )

        return answer

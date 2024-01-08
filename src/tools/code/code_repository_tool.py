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
        display_name="Look Up File in Repository",
        requires_repository=True,
        description="Looks up a file in the repository by partial file name.",
        additional_instructions="Use this tool to find a file in the loaded repository when you don't know the full name (path + name + extension). Provide at least a partial file name.  This tool will return a list of possible matching files.  Set include_summary to `true` if reading a short summary of each possible file would help to narrow down your search.",
    )
    def look_up_file_in_repository(self, partial_file_name: str, include_summary: bool = False):
        """Looks up a file in the repository by partial file name."""
        code_files = self.conversation_manager.code_helper.get_code_files_by_partial_name(
            repository_id=self.conversation_manager.get_selected_repository().id, partial_file_name=partial_file_name
        )
        
        results = ""
        for code_file in code_files:
            results += f"**\n{code_file.code_file_name} (ID: {code_file.id})\n**"
            if include_summary:
                results += f"Summary: {code_file.code_file_summary}\n"
        
        return results
       
       

    @register_tool(
        display_name="Get Repository File List",
        requires_repository=True,
        description="Gets the list of files and directories in a loaded code repository.",
        additional_instructions="Use this tool to get a list of the files and directories in a loaded code repository- good for understanding the structure of the repository.  Set `include_summary` to `true` if you want summaries of each of the files as well.  Note: Unless it is absolutely vital to answer the user's query, don't set `include_summary` to `true`- it will slow things down significantly.",
    )
    def get_repository_file_list(self, include_summary: bool = False):
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
        display_name="Retrieve Codebase Metrics",
        requires_repository=True,
        description="Generates a summary of the entire codebase in a loaded repository.",
        additional_instructions="Use this tool to get a high-level overview of the codebase, including file counts and lines of code.",
    )
    def retrieve_codebase_metrics(self):
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
        display_name="Get Repository Code File",
        requires_repository=True,
        description="Gets a specific code file from a loaded code repository by name or ID.",
        additional_instructions="Provide either the name or the ID of the code file you wish to retrieve.  file_name should be the full name of the file, including the path and extension.  file_id should be the ID of the file.  Either of these can be retrieved using the `Get Repository File List` tool.",
    )
    def get_repository_code_file(self, file_name: str = None, file_id: int = None):
        """Gets a specific code file from a loaded code repository by name or ID."""
        if file_name is not None:
            # Get the code file by name
            code_file = self.conversation_manager.code_helper.get_code_file_by_name(
                code_repo_id=self.conversation_manager.get_selected_repository().id,
                code_file_name=file_name,
            )
        elif file_id is not None:
            # Get the code file by ID
            code_file = self.conversation_manager.code_helper.get_code_file_by_id(
                file_id
            )
        else:
            return "Please provide either a file name or file ID."

        if code_file is None:
            return "Code file not found."

        return {
            "file_name": code_file.code_file_name,
            "file_content": code_file.code_file_content,
        }

    @register_tool(
        display_name="Functionality Locator",
        requires_repository=True,
        description="Locates specific functionality within the codebase.",
        additional_instructions="Provide a description or keywords related to the functionality you're looking for.",
    )
    def locate_functionality_in_repository(
        self, description: str, keywords_list: List[str]
    ):
        """Locates specific functionality within the codebase."""
        try:
            # Use the search_repository_for_file_info tool to find files that may contain the desired functionality
            file_info_list = self.search_repository_for_file_info(
                semantic_similarity_query=description, keywords_list=keywords_list
            )

            # Process the results to extract relevant code snippets
            functionality_snippets = []
            for file_info in file_info_list:
                code_file = self.get_repository_code_file(file_id=file_info["file_id"])

                get_relevant_snippets_prompt = (
                    self.conversation_manager.prompt_manager.get_prompt(
                        "code_general", "GET_RELEVANT_SNIPPETS_TEMPLATE"
                    )
                ).format(
                    code=code_file["file_content"],
                    description=description,
                )

                llm = get_tool_llm(
                    configuration=self.configuration,
                    func_name=self.locate_functionality_in_repository.__name__,
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
                    relevant_snippets = ["No relevant snippets found."]

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
        display_name="Search Repository for File Info",
        requires_repository=True,
        description="Searches the loaded repository and returns a list of file IDs, names, and summaries.",
        additional_instructions="Provide a semantic similarity query and a list of keywords to perform the search.",
    )
    def search_repository_for_file_info(
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
        display_name="Search a Code Repository and Get Code",
        requires_repository=True,
        description="Performs a search of a loaded code repository, and returns all code content related to the user's query.",
        additional_instructions="Performs a search of the loaded code repository using the specified semantic similarity query and keyword list.",
    )
    def search_repository_full_content(
        self,
        semantic_similarity_query: str,
        keywords_list: List[str],
        user_query: str,
    ):
        """Searches the loaded repository for the given query."""

        try:
            # Get the split prompt settings
            split_prompt_settings = self.configuration["tool_configurations"][
                self.search_loaded_repository.__name__
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

    def get_page_or_line(self, document):
        if "page" in document.additional_metadata:
            return f"page='{document.additional_metadata['page']}'"
        elif "start_line" in document.additional_metadata:
            return f"line='{document.additional_metadata['start_line']}'"
        else:
            return ""

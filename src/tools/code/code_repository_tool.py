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
        display_name="Get Repository File List",
        requires_documents=False,
        description="Gets the list of files and directories in a loaded code repository.",
        additional_instructions="Use this tool to get a list of the files and directories in a loaded code repository- good for understanding the structure of the repository.  Set `include_summary` to `true` if you want summaries of each of the files as well.  Note: Unless it is absolutely vital to answer the user's query, don't set `include_summary` to `true`- it will slow things down significantly.",
    )
    def get_repository_file_list(
        self, include_summary: bool = False
    ):
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
        display_name="Get Repository Code File",
        requires_documents=False,
        description="Gets a specific code file from a loaded code repository by name or ID.",
        additional_instructions="Provide either the name or the ID of the code file you wish to retrieve."
    )
    def get_repository_code_file(
        self,
        file_name: str = None,
        file_id: int = None
    ):
        """Gets a specific code file from a loaded code repository by name or ID."""
        if file_name is not None:
            # Get the code file by name
            code_file = self.conversation_manager.code_helper.get_code_file_by_name(
                code_repo_id=self.conversation_manager.get_selected_repository().id,
                code_file_name=file_name
            )
        elif file_id is not None:
            # Get the code file by ID
            code_file = self.conversation_manager.code_helper.get_code_file_by_id(file_id)
        else:
            return 'Please provide either a file name or file ID.'

        if code_file is None:
            return 'Code file not found.'

        return {
            'file_name': code_file.code_file_name,
            'file_content': code_file.code_file_content
        }

    @register_tool(
        display_name="Search Repository for File Info",
        requires_documents=False,
        description="Searches the loaded repository and returns a list of file IDs, names, and summaries.",
        additional_instructions="Provide a semantic similarity query and a list of keywords to perform the search."
    )
    def search_repository_for_file_info(
        self,
        semantic_similarity_query: str,
        keywords_list: List[str]
    ):
        """Searches the loaded repository for the given query and returns file IDs, names, and summaries."""
        try:
            # Perform the search using the existing _search_repository_documents method
            code_file_model_search_results: List[CodeFileModel] = self.conversation_manager.code_helper.search_code_files(
                repository_id=self.conversation_manager.get_selected_repository().id,
                similarity_query=semantic_similarity_query,
                keywords=keywords_list,
                top_k=self.conversation_manager.tool_kwargs.get("search_top_k", 5),
            )

            # Extract the required information from the search results
            file_info_list = [
                {
                    'file_id': result.id,
                    'file_name': result.code_file_name,
                    'file_summary': result.code_file_summary
                }
                for result in code_file_model_search_results
            ]

            # Return the list of file information
            return file_info_list
        except Exception as e:
            return f'An error occurred during the search: {str(e)}'

    @register_tool(
        display_name="Search a Code Repository and Get Code",
        requires_documents=False,
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

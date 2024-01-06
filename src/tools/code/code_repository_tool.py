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

    def list_code_files(self, repository_id: int):
        """Lists the code files in the given repository."""

        code_files = self.conversation_manager.code_helper.get_code_files(
            repository_id=repository_id
        )

        return "\n".join(
            [
                f"### {code_file.code_file_name}\n**Summary:** {code_file.code_file_summary}"
                for code_file in code_files
            ]
        )

    @register_tool(
        display_name="Search a Code Repository",
        requires_documents=False,
        help_text="Performs a search of a loaded code repository.",
        description="Performs a search of a loaded code repository.",
        additional_instructions="Performs a search of the loaded code repository using the specified semantic similarity query and keyword list.",
    )
    def search_loaded_repository(
        self,
        repository_id: int,
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
            repository_id=repository_id,
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

        prompt = self.conversation_manager.prompt_manager.get_prompt(
            "document", "QUESTION_PROMPT_TEMPLATE"
        )

        prompt = prompt.format(
            summaries="\n\n".join(
                [
                    f"### {result.code_file_name}\n**Summary:** {result.code_file_summary}"
                    for result in code_file_model_search_results
                ]
            ),
            question=user_query,
        )

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.search_loaded_repository.__name__,
            streaming=True,
        )

        result = llm.predict(
            prompt, callbacks=self.conversation_manager.agent_callbacks
        )

        return result

    def get_page_or_line(self, document):
        if "page" in document.additional_metadata:
            return f"page='{document.additional_metadata['page']}'"
        elif "start_line" in document.additional_metadata:
            return f"line='{document.additional_metadata['start_line']}'"
        else:
            return ""

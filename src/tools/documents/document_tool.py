import logging
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
from src.ai.prompts.prompt_models.document_summary import (
    DocumentChunkSummaryInput,
    DocumentSummaryOutput,
    DocumentSummaryRefineInput,
)
from src.ai.prompts.prompt_models.document_search import (
    DocumentSearchInput,
    DocumentSearchOutput,
)
from src.ai.prompts.prompt_models.tool_use import (
    AdditionalToolUseInput,
    AdditionalToolUseOutput,
)
from src.ai.prompts.query_helper import QueryHelper
from src.ai.tools.tool_loader import get_available_tools
from src.ai.tools.tool_manager import ToolManager
from src.ai.tools.tool_registry import register_tool, tool_class
from src.utilities.parsing_utilities import parse_json

from src.utilities.token_helper import num_tokens_from_string

from src.db.models.conversation_messages import SearchType
from src.db.models.documents import Documents
from src.db.models.pgvector_retriever import PGVectorRetriever

from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.utilities.llm_helper import get_tool_llm
import src.utilities.configuration_utilities as configuration_utilities


@tool_class
class DocumentTool:
    def __init__(
        self,
        configuration,
        conversation_manager: ConversationManager,
    ):
        self.configuration = configuration
        self.conversation_manager = conversation_manager

    @register_tool(
        display_name="Search Loaded Documents",
        description="Searches the loaded documents for a query.",
        additional_instructions="Searches the loaded files (or the specified file when target_file_id is set).  The user's input should be reworded to be both a keyword search (keywords_list: list of important keywords) and a semantic similarity search query (semantic_similarity_query: a meaningful phrase).  user_query should be a succinctly phrased version of the original user input (phrased as the ultimate question to answer). The target_file_id argument is optional, and can be used to search a specific file if the user has specified one.  Note: This tool only looks at a small subset of the document content in its search, it is not good for getting large chunks of content.",
        help_text="Searches the loaded documents for a query. If the query is directed at a specific document, this will search just that document, otherwise, it will search all loaded documents.",
        requires_documents=True,
        document_classes=["Document", "Code", "Spreadsheet"],
        category="Documents",
    )
    def search_loaded_documents(
        self,
        semantic_similarity_query: str,
        keywords_list: List[str],
        user_query: str,
        target_file_id: int = None,
    ):
        """Searches the loaded files (or the specified file when target_file_id is set) for the given query.
        The target_file_id argument is optional, and can be used to search a specific file if the user has specified one.

        IMPORTANT: If the user has not asked you to look in a specific file, don't use target_file_id.

        Args:
            similarity_query (str): The query to search the loaded documents for (can be a modified version of the original_user_input for searching).
            keywords_list (str): A keyword version of the query to search the loaded documents for
            original_user_input (str): The original user input.  Make sure this is not modified by you!
            target_file_id (int, optional): The file_id if you want to search a specific file. Defaults to None which searches all files.
        """

        # Do we override the file ID?
        target_file_id = self.conversation_manager.tool_kwargs.get(
            "override_file", target_file_id
        )

        try:
            # Get the split prompt settings
            split_prompt_settings = self.configuration["tool_configurations"][
                self.search_loaded_documents.__name__
            ]["additional_settings"]["split_prompt"]

            split_prompts = split_prompt_settings["value"]

            # If there are more than 0 additional prompts, we need to create them
            if split_prompts > 1:
                llm = get_tool_llm(
                    configuration=self.configuration,
                    func_name=self.search_loaded_documents.__name__,
                    streaming=True,
                    # Crank up the frequency and presence penalties to make the LLM give us more variety
                    model_kwargs={
                        "frequency_penalty": 0.7,
                        "presence_penalty": 0.9,
                    },
                    callbacks=self.conversation_manager.agent_callbacks,
                )

                available_tools = get_available_tools(
                    self.configuration, self.conversation_manager
                )

                input_object = AdditionalToolUseInput(
                    tool_name=self.search_loaded_documents.__name__,
                    user_query=user_query,
                    additional_tool_uses=split_prompts
                    - 1,  # -1 to account for the original tool use
                    system_prompt=self.conversation_manager.get_system_prompt(),
                    loaded_documents_prompt=self.conversation_manager.get_loaded_documents_prompt(),
                    selected_repository_prompt=self.conversation_manager.get_selected_repository_prompt(),
                    chat_history_prompt=self.conversation_manager.get_chat_history_prompt(),
                    previous_tool_calls_prompt=self.conversation_manager.get_previous_tool_calls_prompt(),
                    tool_use_description=ToolManager.get_tool_details(
                        self.search_loaded_documents.__name__, available_tools
                    ),
                    initial_tool_use=json.dumps(
                        {
                            "tool_name": self.search_loaded_documents.__name__,
                            "tool_args": {
                                "semantic_similarity_query": semantic_similarity_query,
                                "keywords_list": keywords_list,
                                "user_query": user_query,
                                "target_file_id": target_file_id,
                            },
                        }
                    ),
                )

                query_helper = QueryHelper(self.conversation_manager.prompt_manager)

                result: AdditionalToolUseOutput = query_helper.query_llm(
                    llm=llm,
                    prompt_template_name="ADDITIONAL_TOOL_USE_TEMPLATE",
                    input_class_instance=input_object,
                    output_class_type=AdditionalToolUseOutput,
                )

                # Create a list of search results to add to
                search_results = []

                # Get the original tool use results
                search_results.append(
                    self._search_loaded_documents(
                        semantic_similarity_query=semantic_similarity_query,
                        keywords_list=keywords_list,
                        user_query=user_query,
                        target_file_id=target_file_id,
                    )
                )

                # If there are any additional tool uses, add them to the search results
                for additional_tool_uses in result.additional_tool_use_objects:
                    try:
                        search_results.append(
                            self._search_loaded_documents(
                                semantic_similarity_query=additional_tool_uses.tool_args[
                                    "semantic_similarity_query"
                                ],
                                keywords_list=additional_tool_uses.tool_args[
                                    "keywords_list"
                                ],
                                user_query=additional_tool_uses.tool_args["user_query"],
                                target_file_id=target_file_id,
                            )
                        )
                    except:
                        pass

                return search_results
        except:
            pass

        return self._search_loaded_documents(
            semantic_similarity_query=semantic_similarity_query,
            keywords_list=keywords_list,
            user_query=user_query,
            target_file_id=target_file_id,
        )

    def _search_loaded_documents(
        self,
        semantic_similarity_query: str,
        keywords_list: List[str],
        user_query: str,
        target_file_id: int = None,
    ):
        search_type = self.conversation_manager.tool_kwargs.get("search_type", "Hybrid")

        keyword_documents = []
        if (search_type == "Hybrid" or search_type == "Keyword") and len(
            keywords_list
        ) > 0:
            keyword_documents = (
                self.conversation_manager.documents_helper.search_document_embeddings(
                    search_query=keywords_list,
                    collection_id=self.conversation_manager.collection_id,
                    search_type=SearchType.Keyword,
                    top_k=self.conversation_manager.tool_kwargs.get("search_top_k", 5),
                    target_file_id=target_file_id,
                )
            )

        similarity_documents = []
        if (
            search_type == "Hybrid"
            or search_type == "Similarity"
            and semantic_similarity_query.strip() != ""
        ):
            if semantic_similarity_query and semantic_similarity_query.strip() != "":
                similarity_documents = self.conversation_manager.documents_helper.search_document_embeddings(
                    search_query=semantic_similarity_query,
                    collection_id=self.conversation_manager.collection_id,
                    search_type=SearchType.Similarity,
                    top_k=self.conversation_manager.tool_kwargs.get("search_top_k", 5),
                    target_file_id=target_file_id,
                )

        # De-dupe the documents
        combined_documents = []
        document_ids = []
        for document in keyword_documents:
            if document.id not in document_ids:
                combined_documents.append(document)
                document_ids.append(document.id)

        for document in similarity_documents:
            if document.id not in document_ids:
                combined_documents.append(document)
                document_ids.append(document.id)

        # Examine each of the documents to see if they have anything relating to the original query
        # TODO: Split the documents up into chunks that fit within the max tokens - the completion no matter what the top_k is

        summaries = []

        for document in combined_documents:
            page_or_line = self.get_page_or_line(document)
            summaries.append(
                f"CONTENT: \n{document.document_text}\nSOURCE: file_id='{document.file_id}', file_name='{document.document_name}' {page_or_line}"
            )

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.search_loaded_documents.__name__,
            streaming=True,
            callbacks=self.conversation_manager.agent_callbacks,
        )

        input_object = DocumentSearchInput(summaries=summaries, question=user_query)

        query_helper = QueryHelper(self.conversation_manager.prompt_manager)

        result: DocumentSearchOutput = query_helper.query_llm(
            llm=llm,
            prompt_template_name="QUESTION_PROMPT_TEMPLATE",
            input_class_instance=input_object,
            output_class_type=DocumentSearchOutput,
        )

        return result

    def generate_detailed_document_chunk_summary(self, chunk_text: str, llm) -> str:
        input_object = DocumentChunkSummaryInput(chunk_text=chunk_text)

        query_helper = QueryHelper(self.conversation_manager.prompt_manager)
        result = query_helper.query_llm(
            llm=llm,
            prompt_template_name="DETAILED_DOCUMENT_CHUNK_SUMMARY_TEMPLATE",
            input_class_instance=input_object,
            output_class_type=DocumentSummaryOutput,
        )

        return result.summary

    # TODO: Replace this summarize with a summarize call when ingesting documents.  Store the summary in the DB for retrieval here.
    @register_tool(
        display_name="Summarize Entire Document",
        description="Summarizes an entire document.",
        additional_instructions="This tool should only be used for getting a very general summary of an entire document. Do not use this tool for specific queries about topics, roles, or details. Instead, directly search the loaded documents for specific information related to the user's query. The target_file_id argument is required.",
        help_text="Summarizes an entire document using one of the summarization methods.  ⚠️ If you did not ingest your documents with the summary turned on, this can be slow and expensive, as it will process the entire document.",
        document_classes=["Code", "Spreadsheet", "Document"],
        requires_documents=True,
        category="Documents",
    )
    def summarize_entire_document(self, target_file_id: int):
        """Useful for getting a summary of an entire specific document.  The target_file_id argument is required.

        Args:

            target_file_id (int): The file_id you got from the list of loaded files"""

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.summarize_entire_document.__name__,
            streaming=True,
            # callbacks=self.conversation_manager.agent_callbacks,
        )

        return self.summarize_entire_document_with_llm(llm, target_file_id)

    def summarize_entire_document_with_llm(self, llm, target_file_id: int):
        # Create the documents class for the retriever
        documents = Documents()
        file = documents.get_file(target_file_id)

        # Is there a summary already?  If so, return that instead of re-running the summarization.
        if file.file_summary and file.file_summary != "":
            return file.file_summary

        # Get the document chunks
        document_chunks = documents.get_document_chunks_by_file_id(
            target_file_id=target_file_id
        )

        existing_summary = "No summary yet!"

        # Are there already document chunk summaries?
        for chunk in document_chunks:
            if not chunk.document_text_has_summary:
                # Summarize the chunk
                summary_chunk = self.generate_detailed_document_chunk_summary(
                    chunk_text=chunk.document_text, llm=llm
                )
                documents.set_document_text_summary(
                    chunk.id, summary_chunk, self.conversation_manager.collection_id
                )

            input_object = DocumentSummaryRefineInput(
                text=chunk.document_text, existing_summary=existing_summary
            )

            query_helper = QueryHelper(self.conversation_manager.prompt_manager)

            result = query_helper.query_llm(
                llm=llm,
                prompt_template_name="DOCUMENT_REFINE_TEMPLATE",
                input_class_instance=input_object,
                output_class_type=DocumentSummaryOutput,
            )

            existing_summary = result.summary

        # Put the summary into the DB so we don't have to re-run this.
        documents.update_file_summary_and_class(
            file_id=file.id,
            summary=existing_summary,
            classification=file.file_classification,
        )

        return existing_summary

    def summarize_search_topic(self, query: str, original_user_query: str):
        """Useful for getting a summary of a topic or query from the user.
        This looks at all loaded documents for the topic specified by the query and return a summary of that topic.

        Args:

            query (str, Required): The query to search the loaded documents for (this can be a modified version of the original_user_query for searching).
            original_user_query (str, Required): The original user input.  Make sure this is not modified by you!
        """
        # Create the documents class for the retriever
        documents = Documents()

        document_models = documents.search_document_embeddings(
            search_query=query,
            collection_id=self.conversation_manager.collection_id,
            search_type=self.conversation_manager.tool_kwargs.get(
                "search_type", SearchType.Similarity
            ),
            target_file_id=self.conversation_manager.tool_kwargs.get(
                "override_file", None
            ),
            top_k=self.conversation_manager.tool_kwargs.get("search_top_k", 5),
        )

        # Convert the document models to Document classes
        docs = []
        for doc in document_models:
            docs.append(
                Document(
                    page_content=doc.document_text, metadata=doc.additional_metadata
                )
            )

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.summarize_search_topic.__name__,
            streaming=True,
            # callbacks=self.conversation_manager.agent_callbacks,
        )

        summary = self.refine_summarize(llm=llm, query=query, docs=docs)

        return summary

    def refine_summarize(self, llm, docs, query: str | None = None):
        if query is None:
            refine_prompt = "SIMPLE_DOCUMENT_REFINE_PROMPT"
        else:
            refine_prompt = "SIMPLE_REFINE_PROMPT"

        chain = load_summarize_chain(
            llm=llm,
            chain_type="refine",
            question_prompt=self.conversation_manager.prompt_manager.get_prompt_by_template_name(
                "DETAILED_SUMMARIZE_PROMPT",
            ),
            refine_prompt=self.conversation_manager.prompt_manager.get_prompt_by_template_name(
                refine_prompt
            ),
            return_intermediate_steps=True,
            input_key="input_documents",
            output_key="output_text",
            verbose=True,
        )

        if query is None:
            result = chain({"input_documents": docs}, return_only_outputs=True)
        else:
            result = chain(
                {"input_documents": docs, "query": query}, return_only_outputs=True
            )

        return result["output_text"]

    @register_tool(
        display_name="List Documents",
        description="Lists all loaded documents.",
        help_text="Lists all loaded documents.",
        requires_documents=False,
        category="Documents",
    )
    def list_documents(self):
        """Useful for discovering which documents or files are loaded or otherwise available to you.
        Always use this tool to get the file ID (if you don't already know it) before calling anything else that requires it.
        """

        return "The loaded documents I have access to are:\n\n-" + "\n-".join(
            self.conversation_manager.get_loaded_documents_for_display()
        )

    def get_page_or_line(self, document):
        if "page" in document.additional_metadata:
            return f"page='{document.additional_metadata['page']}'"
        elif "start_line" in document.additional_metadata:
            return f"line='{document.additional_metadata['start_line']}'"
        else:
            return ""

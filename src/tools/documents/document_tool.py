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
from src.utilities.parsing_utilities import parse_json

from src.utilities.token_helper import num_tokens_from_string

from src.db.models.conversations import SearchType
from src.db.models.documents import Documents
from src.db.models.pgvector_retriever import PGVectorRetriever

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_tool_llm
import src.utilities.configuration_utilities as configuration_utilities


class DocumentTool:
    def __init__(
        self,
        configuration,
        interaction_manager: InteractionManager,
    ):
        self.configuration = configuration
        self.interaction_manager = interaction_manager

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
        target_file_id = self.interaction_manager.tool_kwargs.get(
            "override_file", target_file_id
        )

        try:
            # Get the number of additional prompts that should be created to search the loaded documents
            refactor_prompt_settings = self.configuration["tool_configurations"][
                self.search_loaded_documents.__name__
            ]["refactor_prompt_settings"]

            split_prompts = 0
            for setting in refactor_prompt_settings:
                if setting["name"] == "Split Prompt":
                    split_prompts = setting["value"]
                    break

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
                )

                additional_prompt_prompt = (
                    self.interaction_manager.prompt_manager.get_prompt(
                        "prompt_refactoring", "ADDITIONAL_PROMPTS_TEMPLATE"
                    )
                )
                
                def get_chat_history():
                    if self.interaction_manager:
                        return (
                            self.interaction_manager.conversation_token_buffer_memory.buffer_as_str
                        )
                    else:
                        return "No chat history."

                split_prompts = llm.predict(
                    additional_prompt_prompt.format(
                        additional_prompts=split_prompts,
                        user_query=user_query,
                        chat_history=get_chat_history(),
                    ),
                    callbacks=self.interaction_manager.agent_callbacks,
                )

                split_prompts = parse_json(split_prompts, llm)

                results = []
                for prompt in split_prompts["prompts"]:
                    results.append(
                        self._search_loaded_documents(
                            semantic_similarity_query=prompt[
                                "semantic_similarity_query"
                            ],
                            keywords_list=prompt["keywords_list"],
                            user_query=prompt["query"],
                            target_file_id=target_file_id,
                        )
                    )

                return "\n".join(results)
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
        search_type = self.interaction_manager.tool_kwargs.get("search_type", "Hybrid")

        keyword_documents = []
        if search_type == "Hybrid" or search_type == "Keyword":
            keyword_documents = (
                self.interaction_manager.documents_helper.search_document_embeddings(
                    search_query=keywords_list,
                    collection_id=self.interaction_manager.collection_id,
                    search_type=SearchType.Keyword,
                    top_k=self.interaction_manager.tool_kwargs.get("search_top_k", 5),
                    target_file_id=target_file_id,
                )
            )

        similarity_documents = []
        if search_type == "Hybrid" or search_type == "Similarity":
            similarity_documents = (
                self.interaction_manager.documents_helper.search_document_embeddings(
                    search_query=semantic_similarity_query,
                    collection_id=self.interaction_manager.collection_id,
                    search_type=SearchType.Similarity,
                    top_k=self.interaction_manager.tool_kwargs.get("search_top_k", 5),
                    target_file_id=target_file_id,
                )
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

        prompt = self.interaction_manager.prompt_manager.get_prompt(
            "document", "QUESTION_PROMPT_TEMPLATE"
        )

        # prompt_tokens = num_tokens_from_string(prompt + original_user_input)

        # Examine each of the documents to see if they have anything relating to the original query
        # TODO: Split the documents up into chunks that fit within the max tokens - the completion no matter what the top_k is

        summaries = []

        for document in combined_documents:
            page_or_line = self.get_page_or_line(document)
            summaries.append(
                f"CONTENT: \n{document.document_text}\nSOURCE: file_id='{document.file_id}', file_name='{document.document_name}' {page_or_line}"
            )

        prompt = prompt.format(summaries="\n\n".join(summaries), question=user_query)

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.search_loaded_documents.__name__,
            streaming=True,
        )

        result = llm.predict(prompt, callbacks=self.interaction_manager.agent_callbacks)

        return result

    def generate_detailed_document_chunk_summary(self, document_text: str, llm) -> str:
        summary = llm.predict(
            self.interaction_manager.prompt_manager.get_prompt(
                "summary",
                "DETAILED_DOCUMENT_CHUNK_SUMMARY_TEMPLATE",
            ).format(text=document_text),
            callbacks=self.interaction_manager.agent_callbacks,
        )
        return summary

    # TODO: Replace this summarize with a summarize call when ingesting documents.  Store the summary in the DB for retrieval here.
    def summarize_entire_document(self, target_file_id: int):
        """Useful for getting a summary of an entire specific document.  The target_file_id argument is required.

        Args:

            target_file_id (int): The file_id you got from the list of loaded files"""

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.summarize_entire_document.__name__,
            streaming=True,
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

        # Are there already document chunk summaries?
        for chunk in document_chunks:
            if not chunk.document_text_has_summary:
                # Summarize the chunk
                summary_chunk = self.generate_detailed_document_chunk_summary(
                    document_text=chunk.document_text, llm=llm
                )
                documents.set_document_text_summary(
                    chunk.id, summary_chunk, self.interaction_manager.collection_id
                )

        reduce_chain = LLMChain(
            llm=llm,
            prompt=self.interaction_manager.prompt_manager.get_prompt(
                "summary",
                "REDUCE_SUMMARIES_PROMPT",
            ),
        )

        # Takes a list of documents, combines them into a single string, and passes this to an LLMChain
        combine_documents_chain = StuffDocumentsChain(
            llm_chain=reduce_chain, document_variable_name="doc_summaries"
        )

        # Combines and iteravely reduces the document summaries
        reduce_documents_chain = ReduceDocumentsChain(
            # This is final chain that is called.
            combine_documents_chain=combine_documents_chain,
            # If documents exceed context for `StuffDocumentsChain`
            collapse_documents_chain=combine_documents_chain,
            # The maximum number of tokens to group documents into.
            token_max=self.interaction_manager.tool_kwargs.get(
                "max_summary_chunk_tokens", 5000
            ),
        )

        document_chunks = documents.get_document_chunks_by_file_id(target_file_id)

        docs = [
            Document(
                page_content=doc_chunk.document_text_summary,
                metadata=doc_chunk.additional_metadata,
            )
            for doc_chunk in document_chunks
        ]

        summary = reduce_documents_chain.run(docs)

        # Put the summary into the DB so we don't have to re-run this.
        documents.update_file_summary_and_class(
            file_id=file.id, summary=summary, classification=file.file_classification
        )

        return summary

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
            collection_id=self.interaction_manager.collection_id,
            search_type=self.interaction_manager.tool_kwargs.get(
                "search_type", SearchType.Similarity
            ),
            target_file_id=self.interaction_manager.tool_kwargs.get(
                "override_file", None
            ),
            top_k=self.interaction_manager.tool_kwargs.get("search_top_k", 5),
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
            question_prompt=self.interaction_manager.prompt_manager.get_prompt(
                "summary",
                "DETAILED_SUMMARIZE_PROMPT",
            ),
            refine_prompt=self.interaction_manager.prompt_manager.get_prompt(
                "summary", refine_prompt
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

    def list_documents(self):
        """Useful for discovering which documents or files are loaded or otherwise available to you.
        Always use this tool to get the file ID (if you don't already know it) before calling anything else that requires it.
        """

        return "The loaded documents I have access to are:\n\n-" + "\n-".join(
            self.interaction_manager.get_loaded_documents_for_display()
        )

    def search_entire_document(self, target_file_id: int, queries: List[str]):
        """Search the entire document."""

        documents = Documents()

        file = documents.get_file(target_file_id)

        # Get the document chunks
        document_chunks = documents.get_document_chunks_by_file_id(
            target_file_id=target_file_id
        )

        tool_config = configuration_utilities.get_tool_configuration(
            configuration=self.configuration,
            func_name=self.search_entire_document.__name__,
        )

        # TODO: Figure out the right amount of prompt tokens- currently too many causes the LLM to miss things.
        # max_prompt_tokens = (
        #     tool_config["model_configuration"]["max_model_supported_tokens"] * 0.75
        # )
        max_prompt_tokens = 1000

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.search_entire_document.__name__,
            streaming=True,
        )

        questions = "- " + "\n-".join(queries)
        prompt = self.interaction_manager.prompt_manager.get_prompt(
            "document", "SEARCH_ENTIRE_DOCUMENT_TEMPLATE"
        )

        document_chunks_length = len(document_chunks)

        intermediate_results = []
        index = 0
        while index < document_chunks_length:
            previous_context = (
                f"CHUNK {index - 1}:\n{document_chunks[index - 1].document_text}\nSOURCE: file_id='{document_chunks[index - 1].file_id}', file_name='{document_chunks[index - 1].document_name}' {self.get_page_or_line(document_chunks[index - 1])}\n----"
                if index > 0
                else ""
            )

            document_texts = []

            while True:
                document_texts.append(
                    f"CHUNK {index}:\n{document_chunks[index].document_text}\nSOURCE: file_id='{document_chunks[index].file_id}', file_name='{document_chunks[index].document_name}' {self.get_page_or_line(document_chunks[index])}"
                )

                # Get the approximate number of tokens in the prompt
                current_prompt_text = (
                    prompt
                    + "\n"
                    + questions
                    + "\n"
                    + previous_context
                    + "\n"
                    + "\n----\n".join(document_texts)
                )

                total_tokens = num_tokens_from_string(current_prompt_text)

                index += 1

                if total_tokens >= max_prompt_tokens or index >= document_chunks_length:
                    break

            formatted_prompt = prompt.format(
                questions=questions,
                previous_context=previous_context,
                current_context="\n----\n".join(document_texts),
            )

            answer = llm.predict(
                formatted_prompt,
                callbacks=self.interaction_manager.agent_callbacks,
            )

            if not answer.lower().startswith("no relevant information"):
                intermediate_results.append(answer)

        result = (
            f"Searching the document, '{file.file_name}', yielded the following data:\n"
            + "\n".join(intermediate_results)
        )

        return result

    def get_page_or_line(self, document):
        if "page" in document.additional_metadata:
            return f"page='{document.additional_metadata['page']}'"
        elif "start_line" in document.additional_metadata:
            return f"line='{document.additional_metadata['start_line']}'"
        else:
            return ""

from langchain.chains.llm import LLMChain
from langchain.base_language import BaseLanguageModel
from langchain.chains import (
    RetrievalQAWithSourcesChain,
    StuffDocumentsChain,
)
from langchain.schema import Document
from langchain.chains.summarize import load_summarize_chain

from src.db.models.conversations import SearchType
from src.db.models.documents import Documents
from src.db.models.pgvector_retriever import PGVectorRetriever

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_prompt


class DocumentTool:
    def __init__(
        self,
        configuration,
        interaction_manager: InteractionManager,
        llm: BaseLanguageModel,
    ):
        self.configuration = configuration
        self.interaction_manager = interaction_manager
        self.llm = llm

    def search_loaded_documents(
        self,
        original_user_query: str,
        search_query: str = None,
        target_file_id: int = None,
    ):
        """Searches the loaded files for the given query.

        The target_file_id argument is optional, and can be used to search a specific file if the user has specified one.

        IMPORTANT: If the user has not asked you to look in a specific file, don't use target_file_id.

        Args:
            original_user_query (str, required): The original unmodified query input from the user.
            search_query (str, optional): The query, possibly rephrased by you, to search the files for.
            target_file_id (int, optional): The file_id if you want to search a specific file. Defaults to None which searches all files.
        """
        search_kwargs = {
            "interaction_id": self.interaction_manager.interaction_id,
            "collection_id": self.interaction_manager.collection_id,
            "top_k": self.interaction_manager.tool_kwargs.get("search_top_k", 5),
            "search_type": self.interaction_manager.tool_kwargs.get(
                "search_method", SearchType.Similarity
            ),
            "target_file_id": self.interaction_manager.tool_kwargs.get(
                "override_file", target_file_id
            ),
        }

        documents_helper = Documents()

        # Create the documents class for the retriever
        self.pgvector_retriever = PGVectorRetriever(
            vectorstore=documents_helper,
            search_kwargs=search_kwargs,
        )

        qa_chain = LLMChain(
            llm=self.llm,
            prompt=get_prompt(
                self.configuration.model_configuration.llm_type, "QUESTION_PROMPT"
            ),
            verbose=True,
        )

        qa_with_sources = RetrievalQAWithSourcesChain.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.pgvector_retriever,
            chain_type_kwargs={
                "prompt": get_prompt(
                    self.configuration.model_configuration.llm_type, "QUESTION_PROMPT"
                )
            },
        )

        combine_chain = StuffDocumentsChain(
            llm_chain=qa_chain,
            document_prompt=get_prompt(
                self.configuration.model_configuration.llm_type, "DOCUMENT_PROMPT"
            ),
            document_variable_name="summaries",
        )

        qa_with_sources.combine_documents_chain = combine_chain
        qa_with_sources.return_source_documents = True

        results = qa_with_sources({"question": search_query or original_user_query})

        return f"--- BEGIN RESULTS ---\n{results['answer']}.\n\nThe sources used are: {results['sources']}--- END RESULTS ---"

    # TODO: Replace this summarize with a summarize call when ingesting documents.  Store the summary in the DB for retrieval here.
    def summarize_entire_document(self, target_file_id: int):
        """Useful for getting a summary of an entire specific document.  The target_file_id argument is required.

        Args:

            target_file_id (int): The file_id you got from the list of loaded files"""
        # Create the documents class for the retriever
        documents = Documents()
        file = documents.get_file(target_file_id)

        docs = [
            Document(
                page_content=doc_chunk.document_text,
                metadata=doc_chunk.additional_metadata,
            )
            for doc_chunk in documents.get_document_chunks_by_file_id(
                target_file_id=target_file_id
            )
        ]

        tool_kwargs = self.interaction_manager.tool_kwargs
        summarization_type = tool_kwargs.get("summarization_type", "refine")

        summarization_map = {
            "refine": self.refine_summarize,
            "map_reduce": self.map_reduce_summarize,
        }

        summary = summarization_map[summarization_type](llm=self.llm, docs=docs)
        return summary

    def summarize_topic(self, query: str):
        """Useful for getting a summary of a topic or query from the user.  This looks at all loaded documents for the topic specified by the query and return a summary of that topic.

        Args:

            query (str): The original query from the user.
        """
        # Create the documents class for the retriever
        documents = Documents()

        document_models = documents.search_document_embeddings(
            search_query=query,
            collection_id=self.interaction_manager.collection_id,
            search_type=self.interaction_manager.tool_kwargs.get(
                "search_method", SearchType.Similarity
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

        summary = self.refine_summarize(llm=self.llm, query=query, docs=docs)

        response = self.llm.predict(
            f"Using the following context derived by searching documents, answer the user's original query.\n\nCONTEXT:\n{summary}\n\nORIGINAL QUERY:\n{query}\n\nAI: I have examined the context above and have determined the following (my response in Markdown):\n"
        )

        return response

    def map_reduce_summarize(self, query, llm, docs):
        pass
        # chain = load_summarize_chain(
        #     llm=llm,
        #     chain_type="refine",
        #     question_prompt=get_prompt(
        #         self.configuration.model_configuration.llm_type, "SIMPLE_SUMMARIZE_PROMPT"
        #     ),
        #     refine_prompt=get_prompt(
        #         self.configuration.model_configuration.llm_type, "SIMPLE_REFINE_PROMPT"
        #     ),
        #     return_intermediate_steps=True,
        #     input_key="input_documents",
        #     output_key="output_text",
        # )

        # result = chain({"input_documents": docs, "query": query}, return_only_outputs=True)

        # return result["output_text"]

    def refine_summarize(self, llm, docs, query: str | None = None):
        if query is None:
            refine_prompt = "SIMPLE_DOCUMENT_REFINE_PROMPT"
        else:
            refine_prompt = "SIMPLE_REFINE_PROMPT"

        chain = load_summarize_chain(
            llm=llm,
            chain_type="refine",
            question_prompt=get_prompt(
                self.configuration.model_configuration.llm_type,
                "SIMPLE_SUMMARIZE_PROMPT",
            ),
            refine_prompt=get_prompt(
                self.configuration.model_configuration.llm_type, refine_prompt
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

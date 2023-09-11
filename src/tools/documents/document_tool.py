from langchain.chains.llm import LLMChain
from langchain.base_language import BaseLanguageModel
from langchain.chains import (
    RetrievalQAWithSourcesChain,
    StuffDocumentsChain,
)
from langchain.schema import Document
from langchain.chains.summarize import load_summarize_chain

from src.configuration.assistant_configuration import Destination

from src.db.models.conversations import SearchType
from src.db.models.documents import Documents
from src.db.models.pgvector_retriever import PGVectorRetriever

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_prompt

class DocumentTool:
    def __init__(self, destination: Destination, interaction_manager: InteractionManager, llm: BaseLanguageModel):
        self.destination = destination
        self.interaction_manager = interaction_manager
        self.llm = llm

    def search_loaded_documents(
        self,
        query: str,
        target_file_id: int = None,
    ):
        """Searches the loaded documents for the given query.  Use this tool when the user is referring to any loaded document or file in their search for information. The target_file_id argument is optional, and can be used to search a specific file.

        Args:
            query (str): The query you would like to search for.  Input should be a fully formed question.
            target_file_id (int, optional): The file_id you got from the list_documents tool, if you want to search a specific file. Defaults to None which searches all files.
        """
        search_kwargs = {
            "top_k": 10,
            "search_type": SearchType.similarity,
            "interaction_id": self.interaction_manager.interaction_id,
            "collection_id": self.interaction_manager.collection_id,
            "target_file_id": target_file_id,
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
                self.destination.model_configuration.llm_type, "QUESTION_PROMPT"
            ),
            verbose=True,
        )

        qa_with_sources = RetrievalQAWithSourcesChain.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.pgvector_retriever,
            chain_type_kwargs={
                "prompt": get_prompt(
                    self.destination.model_configuration.llm_type, "QUESTION_PROMPT"
                )
            },
        )

        combine_chain = StuffDocumentsChain(
            llm_chain=qa_chain,
            document_prompt=get_prompt(
                self.destination.model_configuration.llm_type, "DOCUMENT_PROMPT"
            ),
            document_variable_name="summaries",
        )

        qa_with_sources.combine_documents_chain = combine_chain
        qa_with_sources.return_source_documents = True

        results = qa_with_sources({"question": query})

        return results["answer"]

    # TODO: Replace this summarize with a summarize call when ingesting documents.  Store the summary in the DB for retrieval here.
    def summarize_entire_document(self, target_file_id: int):
        """Useful for getting a summary of an entire specific document.  The target_file_id argument is required.

        Args:

            target_file_id (int): The file_id you got from the list of loaded files"""
        # Create the documents class for the retriever
        documents = Documents()
        file = documents.get_file(target_file_id)

        return f"The file is classified as: '{file.file_classification}'.  What follows is a brief summary generated from a portion of the document:\n\n{file.file_summary}"

    def summarize_topic(self, query: str):
        """Useful for getting a summary of a topic or query from the user.  This look at all loaded documents for the topic specified by the query and return a summary of that topic.

        Args:

            query (str): The original query from the user.
        """
        # Create the documents class for the retriever
        documents = Documents()

        document_models = documents.search_document_embeddings(
            search_query=query,
            search_type=SearchType.similarity,
            collection_id=self.interaction_manager.collection_id,
            target_file_id=None,
            top_k=10
        )

        # Convert the document models to Document classes
        docs = []
        for doc in document_models:
            docs.append(Document(page_content=doc.document_text, metadata=doc.additional_metadata))

        summary =  self.refine_summarize(llm=self.llm, query=query, docs=docs)

        response = self.llm.predict(f"Using the following context derived by searching documents, answer the user's original query.\n\nCONTEXT:\n{summary}\n\nORIGINAL QUERY:\n{query}\n\nAI: I have examined the context above and have determined the following (my response in Markdown):\n")

        return response

    def refine_summarize(self, query, llm, docs):
        chain = load_summarize_chain(
            llm=llm,
            chain_type="refine",
            question_prompt=get_prompt(
                self.destination.model_configuration.llm_type, "SIMPLE_SUMMARIZE_PROMPT"
            ),
            refine_prompt=get_prompt(
                self.destination.model_configuration.llm_type, "SIMPLE_REFINE_PROMPT"
            ),
            return_intermediate_steps=True,
            input_key="input_documents",
            output_key="output_text",
        )

        result = chain({"input_documents": docs, "query": query}, return_only_outputs=True)

        return result["output_text"]    
    
    def list_documents(self):
        """Useful for discovering which documents or files are loaded or otherwise available to you.
        Always use this tool to get the file ID (if you don't already know it) before calling anything else that requires it.
        """

        return "The loaded documents I have access to are:\n-" + "\n-".join(
            self.interaction_manager.get_loaded_documents_for_display()
        )
    

    # def create_single_line_summary(self, llm, docs):        

    #     llm_chain = LLMChain(
    #         llm=llm,
    #         prompt=get_prompt(
    #             self.destination.model_configuration.llm_type,
    #             "SINGLE_LINE_SUMMARIZE_PROMPT",
    #         ),
    #     )

    #     stuff_chain = StuffDocumentsChain(
    #         llm_chain=llm_chain, document_variable_name="text"
    #     )

    #     return stuff_chain.run(docs)
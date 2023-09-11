import logging
import json
from uuid import UUID
from typing import List

from langchain.chains.llm import LLMChain
from langchain.base_language import BaseLanguageModel
from langchain.prompts import PromptTemplate
from langchain.tools import StructuredTool, Tool
from langchain.chains import (
    RetrievalQA,
    RetrievalQAWithSourcesChain,
    StuffDocumentsChain,
    create_qa_with_sources_chain,
)
from langchain.schema import Document, HumanMessage, AIMessage
from langchain.chains.summarize import load_summarize_chain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.agents import (
    initialize_agent,
    AgentType,
    AgentExecutor,
    AgentOutputParser,
)

from src.configuration.assistant_configuration import Destination

from src.db.models.conversations import SearchType
from src.db.models.documents import Documents
from src.db.models.users import User
from src.db.models.pgvector_retriever import PGVectorRetriever

from src.ai.destinations.output_parser import CustomStructuredChatOutputParserWithRetries
from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm, get_prompt
from src.ai.system_info import get_system_information
from src.ai.destination_route import DestinationRoute
from src.ai.system_info import get_system_information
from src.ai.destinations.destination_base import DestinationBase
from src.ai.callbacks.token_management_callback import TokenManagementCallbackHandler
from src.ai.callbacks.agent_callback import AgentCallback
from src.utilities.token_helper import simple_get_tokens_for_message


class CodeTool:
    def __init__(
        self,
        destination: Destination,
        interaction_manager: InteractionManager,
        llm: BaseLanguageModel,
    ):
        self.destination = destination
        self.interaction_manager = interaction_manager
        self.llm = llm

    def code_dependencies(self, target_file_id: int):
        """Useful for getting the dependencies of a specific loaded code file.  This tool will give you a list of all the dependencies for the code file you specify.

        Don't use this on anything that isn't classified as 'Code'.

        Args:
            target_file_id (int): The file ID you would like to get the dependencies for.
        """
        documents = Documents()

        # Get the list of documents        
        document_chunks = documents.get_document_chunks_by_file_id(
            collection_id=self.interaction_manager.collection_id,
            target_file_id=target_file_id,
        )

        # Get the list of includes
        includes = []
        for doc in document_chunks:
            # strip the filename from the path
            if doc.additional_metadata["type"] == "MODULE":
                for include in doc.additional_metadata["includes"]:
                    filename = include.split("/")[-1]
                    if filename not in includes:
                        includes.append(filename)

        # return the list of includes
        #"The dependencies for this file are:\n\n" + 
        return "\n".join(includes)

    def code_structure(
        self,
        query: str,
        target_file_id: int,
        code_type: str = None,
    ):
        """Useful for understanding the high-level structure of a specific loaded code file.  Use this tool before using the 'code_detail' tool.
        This tool will give you a list of module names, function signatures, and class method signatures.
        You can use the signature of any of these to get more details about that specific piece of code when calling code_detail.

        Don't use this tool on anything that isn't classified as 'Code'.

        Args:
            query (str): The original query from the user.
            target_file_id (int): REQUIRED! The file ID you would like to get the code structure for.
            code_type (str, optional): Valid code_type arguments are 'MODULE', 'FUNCTION_DECLARATION', and 'CLASS_METHOD'. When left empty, the code structure will be returned in its entirety.
        """
        documents = Documents()

        try:
            document_chunks = documents.get_document_chunks_by_file_id(
                self.interaction_manager.collection_id, target_file_id
            )

            code_structure = ""

            # Create a list of unique metadata entries from the document chunks
            full_metadata_list = []
            modules = []
            functions = []
            class_methods = []
            others = []

            self.get_metadata(
                full_metadata_list,
                modules,
                functions,
                class_methods,
                others,
                document_chunks,
            )

            # Custom sorting key function
            def custom_sorting_key(item):
                # Assign a higher value (e.g., 0) to "MODULE" type, lower value (e.g., 1) to others
                return 0 if item["type"] == "MODULE" else 1

            code_structure = "The code structure is:\n\n"

            if code_type is not None:
                if code_type == "MODULE":
                    code_structure += (
                        "Modules: "
                        + ", ".join([m["filename"] for m in modules])
                        + "\n\n"
                    )
                elif code_type == "FUNCTION_DECLARATION":
                    code_structure += (
                        "Functions: "
                        + ", ".join([f["signature"] for f in functions])
                        + "\n\n"
                    )
                elif code_type == "CLASS_METHOD":
                    code_structure += (
                        "Class Methods: "
                        + ", ".join([c["signature"] for c in class_methods])
                        + "\n\n"
                    )
                elif code_type == "OTHER":
                    code_structure += (
                        "Other: " + ", ".join([o["signature"] for o in others]) + "\n\n"
                    )
            else:
                # Sort the list using the custom sorting key
                sorted_data = sorted(full_metadata_list, key=custom_sorting_key)

                # Iterate through everything and put it into the prompt
                code_structure += "\n".join(
                    [f"{m['type']}: {m['signature']}" for m in sorted_data]
                )

            result = self.llm.predict(
                f"{code_structure}\n\nUsing the code structure above, answer this query:\n\n{query}\n\nAI: I have examined the code structure above and have determined the following (my response in Markdown):\n"
            )

            return result
        except Exception as e:
            logging.error(f"Error getting code structure: {e}")
            return f"There was an error getting the code structure: {e}"

    def get_metadata(
        self,
        full_metadata_list,
        modules,
        functions,
        class_methods,
        others,
        document_chunks,
    ):
        for doc in document_chunks:
            if doc.additional_metadata is not None:
                metadata = doc.additional_metadata
                if metadata not in full_metadata_list:
                    full_metadata_list.append(metadata)
                    if metadata["type"] == "MODULE":
                        modules.append(metadata)
                    elif metadata["type"] == "FUNCTION_DEFINITION":
                        functions.append(metadata)
                    elif metadata["type"] == "CLASS_METHOD":
                        class_methods.append(metadata)
                    else:
                        others.append(metadata)

    def code_details(
        self,
        target_file_id: int,
        target_signature: str,
    ):
        """Useful for getting the details of a specific piece of code in a loaded code file.  Use this tool after using the 'code_structure' tool.  This tool will give you the code details for the specific piece of code you requested.  You can get the signature of any piece of code from the 'code_structure' tool.

        Don't use this on anything that isn't classified as 'Code'.

        Args:
            target_file_id (int): The file ID you would like to get the code details for.
            target_signature (str): The signature of the piece of code you would like to get the details for. Valid values for this argument are the signatures returned by the 'code_structure' tool.
        """
        documents = Documents()

        try:
            document_chunks = documents.get_document_chunks_by_file_id(
                self.interaction_manager.collection_id, target_file_id
            )

            code_details = f"The code details for {target_signature} is:\n\n"

            # Find the document chunk that matches the target signature
            target_document_chunk = None
            for doc in document_chunks:
                if doc.additional_metadata is not None:
                    metadata = doc.additional_metadata
                    if target_signature in metadata["signature"]:
                        target_document_chunk = doc
                        break

            if target_document_chunk is None:
                # Sometimes the AI is stupid and gets in here before it has a signature.  Let's try to help it out.
                # Fall back to searching the code file for the signature the AI passed in
                related_documents = documents.search_document_embeddings(
                    target_signature,
                    SearchType.similarity,
                    self.interaction_manager.collection_id,
                    target_file_id,
                    top_k=20,  # TODO: ... magic number
                )

                full_metadata_list = []
                modules = []
                functions = []
                class_methods = []
                others = []

                self.get_metadata(
                    full_metadata_list,
                    modules,
                    functions,
                    class_methods,
                    others,
                    related_documents,
                )

                # TODO: ... magic number
                # Loop through the full metadata list and add it to the output, checking to see if we're over the arbitrary token limit of 1000
                for doc in related_documents:
                    if simple_get_tokens_for_message(code_details) > 1000:
                        break
                    metadata = doc.additional_metadata
                    if metadata["type"] != "MODULE":
                        code_details += metadata["text"] + "\n\n"

                # If we still can't find anything, tell the AI it's behaving badly
                return (
                    "I found the following code, but no code exists with that signature!  You were probably being a bad AI and NOT following the instructions where I told you to use the code_structure tool first!  BAD AI!\n\n"
                    + code_details
                )
            else:
                code_details += target_document_chunk.document_text

                return code_details
        except Exception as e:
            logging.error(f"Error getting code details: {e}")
            return f"There was an error getting the code details: {e}"

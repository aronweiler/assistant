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

from configuration.assistant_configuration import Destination

from db.models.conversations import SearchType
from db.models.documents import Documents
from db.models.users import User
from db.models.pgvector_retriever import PGVectorRetriever

from ai.destinations.output_parser import CustomStructuredChatOutputParserWithRetries
from ai.interactions.interaction_manager import InteractionManager
from ai.llm_helper import get_llm
from ai.system_info import get_system_information
from ai.destination_route import DestinationRoute
from ai.system_info import get_system_information
from ai.destinations.destination_base import DestinationBase
from ai.callbacks.token_management_callback import TokenManagementCallbackHandler
from ai.callbacks.agent_callback import AgentCallback
from ai.prompts import (
    AGENT_TEMPLATE,
    SIMPLE_SUMMARIZE_PROMPT,
    SIMPLE_REFINE_PROMPT,
    SINGLE_LINE_SUMMARIZE_PROMPT,
    REPHRASE_TO_KEYWORDS_TEMPLATE,
    TOOLS_SUFFIX,
    REPHRASE_TEMPLATE,
    TOOLS_FORMAT_INSTRUCTIONS,
    QUESTION_PROMPT,
    COMBINE_PROMPT,
    DOCUMENT_PROMPT,
)

from utilities.token_helper import simple_get_tokens_for_message


class DocumentsAI(DestinationBase):
    """A document-using AI that uses an LLM to generate responses"""

    def __init__(
        self,
        destination: Destination,
        interaction_id: int,
        user_email: str,
        db_env_location: str,
        streaming: bool = False,
    ):
        self.destination = destination

        self.agent_callback = AgentCallback()
        self.token_management_handler = TokenManagementCallbackHandler()

        self.llm = get_llm(
            destination.model_configuration,
            callbacks=[self.token_management_handler],
            tags=["documents"],
            streaming=streaming,
        )

        self.interaction_manager = InteractionManager(
            interaction_id,
            user_email,
            self.llm,
            db_env_location,
            destination.model_configuration.max_conversation_history_tokens,
        )

        self.create_document_tools()

        self.agent = initialize_agent(
            tools=self.document_tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            human_message_template=AGENT_TEMPLATE,
            agent_kwargs={
                "suffix": TOOLS_SUFFIX,
                "format_instructions": TOOLS_FORMAT_INSTRUCTIONS,
                "output_parser": CustomStructuredChatOutputParserWithRetries(),
                "input_variables": [
                    "input",
                    "agent_chat_history",
                    "agent_scratchpad",
                    "system_information",
                ],
            },
        )

        # Agents should have their own memory (containing past tool runs or other info) that is combined with the conversation memory
        # Combine with the overall conversation memory
        # agent.memory = CombinedMemory(memories=[memory, agent_memory])

        # Set the memory on the agent tools callback so that it can manually add entries
        # self.agent_tools_callback.memory = agent_memory.memory

    def create_document_tools(self):
        self.document_tools = [
            StructuredTool.from_function(
                func=self.search_loaded_documents,
                callbacks=[self.agent_callback],
                return_direct=True,
            ),
            # TODO: Make this better... currently only uses the initial summary generated on ~10 pages / splits
            StructuredTool.from_function(
                func=self.summarize_document,
                callbacks=[self.agent_callback],
                return_direct=True,
            ),
            StructuredTool.from_function(
                func=self.list_documents,
                callbacks=[self.agent_callback],
                return_direct=True,
            ),
            StructuredTool.from_function(
                func=self.code_structure, callbacks=[self.agent_callback],
                return_direct=True
            ),
            StructuredTool.from_function(
                func=self.code_details, callbacks=[self.agent_callback]
            ),
        ]

    def run(
        self,
        input: str,
        collection_id: str = None,
        llm_callbacks: list = [],
        agent_callbacks: list = [],
    ):
        self.interaction_manager.collection_id = collection_id
        rephrased_input = self.rephrase_query_to_standalone(input)

        results = self.agent.run(
            input=rephrased_input,
            system_information=get_system_information(
                self.interaction_manager.user_location
            ),
            user_name=self.interaction_manager.user_name,
            user_email=self.interaction_manager.user_email,
            agent_chat_history="\n".join(
                [
                    f"{'AI' if m.type == 'ai' else f'{self.interaction_manager.user_name} ({self.interaction_manager.user_email})'}: {m.content}"
                    for m in self.interaction_manager.conversation_token_buffer_memory.chat_memory.messages[
                        -4:
                    ]
                ]
            ),
            callbacks=agent_callbacks,
        )

        # Adding this after the run so that the agent can't see it in the history
        self.interaction_manager.conversation_token_buffer_memory.chat_memory.add_user_message(
            input
        )  # .add_message(HumanMessage(input))

        try:
            # Try loading the result as json (sometimes it doesn't run the tool on its own)
            results = json.loads(results)

            # Find the tool
            for tool in self.document_tools:
                if tool.name.lower() == results["action"].lower():
                    # Run the tool
                    try:
                        results = tool.func(**results["action_input"])
                        break
                    except Exception as es:
                        print(f"Error running tool {tool.name} in documents AI, {es}")
                        results = (
                            f"Error running tool {tool.name} in documents AI, {es}"
                        )
        except Exception as e:
            print(
                f"Couldn't load results as json, which probably means it's just a text result."
            )

        print(results)
        self.interaction_manager.conversation_token_buffer_memory.chat_memory.add_ai_message(
            results
        )  # postgres_chat_message_history.add_message(AIMessage(results))

        return results

    def list_documents(self):
        """Useful for discovering which documents or files are loaded or otherwise available to you.
        Always use this tool to get the file ID (if you don't already know it) before calling anything else that requires it.
        """

        return "The loaded documents I have access to are:\n-" + "\n-".join(
            self.interaction_manager.get_loaded_documents_for_display()
        )

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

        # Create the documents class for the retriever
        self.pgvector_retriever = PGVectorRetriever(
            vectorstore=Documents(self.interaction_manager.db_env_location),
            search_kwargs=search_kwargs,
        )

        qa_chain = LLMChain(llm=self.llm, prompt=QUESTION_PROMPT, verbose=True)

        qa_with_sources = RetrievalQAWithSourcesChain.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.pgvector_retriever,
            chain_type_kwargs={"prompt": QUESTION_PROMPT},
        )

        combine_chain = StuffDocumentsChain(
            llm_chain=qa_chain,
            document_prompt=DOCUMENT_PROMPT,
            document_variable_name="summaries",
        )

        qa_with_sources.combine_documents_chain = combine_chain
        qa_with_sources.return_source_documents = True

        results = qa_with_sources({"question": query})

        return results["answer"]

    # TODO: Replace this summarize with a summarize call when ingesting documents.  Store the summary in the DB for retrieval here.
    def summarize_document(self, target_file_id: int):
        """Useful for getting a summary of a specific loaded document.  Use this tool when the user is referring to any loaded document or file in their search for information.  The target_file_id argument is required, and can be used to search a specific file.

        Args:

            target_file_id (int): The file_id you got from the list of loaded files"""
        # Create the documents class for the retriever
        documents = Documents(self.interaction_manager.db_env_location)
        file = documents.get_file(target_file_id)

        return f"The file is classified as: '{file.file_classification}'.  What follows is a brief summary generated from a portion of the document:\n\n{file.file_summary}"

    def refine_summarize(self, llm, docs):
        chain = load_summarize_chain(
            llm=llm,
            chain_type="refine",
            question_prompt=SIMPLE_SUMMARIZE_PROMPT,
            refine_prompt=SIMPLE_REFINE_PROMPT,
            return_intermediate_steps=True,
            input_key="input_documents",
            output_key="output_text",
        )

        result = chain({"input_documents": docs}, return_only_outputs=True)

        return result["output_text"]

    def summarize(self, llm, docs):
        llm_chain = LLMChain(llm=llm, prompt=SINGLE_LINE_SUMMARIZE_PROMPT)

        stuff_chain = StuffDocumentsChain(
            llm_chain=llm_chain, document_variable_name="text"
        )

        return stuff_chain.run(docs)

    def rephrase_query_to_standalone(self, query):
        # Rephrase the query so that it is stand-alone
        # Use the llm to rephrase, adding in the conversation memory for context
        rephrase_results = self.llm.predict(
            REPHRASE_TEMPLATE.format(
                input=query,
                chat_history="\n".join(
                    [
                        f"{'AI' if m.type == 'ai' else f'{self.interaction_manager.user_name} ({self.interaction_manager.user_email})'}: {m.content}"
                        for m in self.interaction_manager.conversation_token_buffer_memory.buffer_as_messages[
                            -8:
                        ]
                    ]
                ),
                system_information=get_system_information(
                    self.interaction_manager.user_location
                ),
                user_name=self.interaction_manager.user_name,
                user_email=self.interaction_manager.user_email,
                loaded_documents="\n".join(
                    self.interaction_manager.get_loaded_documents_for_reference()
                ),
            )
        )

        return rephrase_results

    # def rephrase_query_to_search_keywords(self, query, user):
    #     # Rephrase the query so that it is stand-alone
    #     # Use the llm to rephrase, adding in the conversation memory for context
    #     rephrase_results = self.llm.predict(
    #         REPHRASE_TO_KEYWORDS_TEMPLATE.format(
    #             input=query,
    #             chat_history="\n".join(
    #                 [
    #                     f"{'AI' if m.type == 'ai' else f'{user.name} ({user.email})'}: {m.content}"
    #                     for m in self.postgres_chat_message_history.messages[-16:]
    #                 ]
    #             ),
    #             system_information=self.get_system_information(user),
    #             user_name=user.name,
    #             user_email=user.email,
    #             loaded_documents="\n".join(
    #                 self.get_loaded_documents(self.collection_id)
    #             ),
    #         )
    #     )

    #     return rephrase_results

    def code_structure(
        self,
        query: str,
        target_file_id: int,
        code_type: str = None,        
    ):
        """Useful for understanding the high-level structure of a specific loaded code file.  Use this tool before using the 'code_detail' tool.
        This tool will give you a list of module names, function signatures, and class method signatures.
        You can use the signature of any of these to get more details about that specific piece of code when calling code_detail.

        Don't use this on anything that isn't classified as 'Code'.

        Args:
            query (str): The query to ask of the code structure.  Input should be a fully formed question.
            target_file_id (int): The file ID you would like to get the code structure for.
            code_type (str, optional): Valid code_type arguments are 'MODULE', 'FUNCTION_DECLARATION', and 'CLASS_METHOD'.
        """
        documents = Documents(self.interaction_manager.db_env_location)

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

        if(code_type is not None):
            if code_type == "MODULE":
                code_structure += (
                    "Modules: " + ", ".join([m["filename"] for m in modules]) + "\n\n"
                )
            elif code_type == "FUNCTION_DECLARATION":
                code_structure += (
                    "Functions: " + ", ".join([f["signature"] for f in functions]) + "\n\n"
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
            code_structure += (
                "\n".join([f"{m['type']}: {m['signature']}" for m in sorted_data])
            )

        result = self.llm.predict(f"{code_structure}\n\nUsing the code structure above, please answer this query:\n\n{query}\n\nAI: I have examined the code structure and have determined the following:\n")

        return result

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
        documents = Documents(self.interaction_manager.db_env_location)

        document_chunks = documents.get_document_chunks_by_file_id(
            self.interaction_manager.collection_id, target_file_id
        )

        code_details = f"The code details for {target_signature} is:\n\n"

        # Find the document chunk that matches the target signature
        target_document_chunk = None
        for doc in document_chunks:
            if doc.additional_metadata is not None:
                metadata = json.loads(doc.additional_metadata)
                if metadata["signature"] == target_signature:
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

            # Loop through the full metadata list and add it to the output, checking to see if we're over the token limit of 1000
            for doc in related_documents:
                if simple_get_tokens_for_message(code_details) > 1000:
                    break
                metadata = json.loads(doc.additional_metadata)
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
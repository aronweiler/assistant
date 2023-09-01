import logging
import json
from uuid import UUID
from typing import List

from langchain.chains.llm import LLMChain
from langchain.base_language import BaseLanguageModel
from langchain.prompts import PromptTemplate
from langchain.tools import StructuredTool, Tool
from langchain.chains import RetrievalQA, StuffDocumentsChain
from langchain.schema import Document, HumanMessage, AIMessage
from langchain.chains.summarize import load_summarize_chain
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

from ai.interactions.interaction_manager import InteractionManager
from ai.llm_helper import get_llm
from ai.system_info import get_system_information
from ai.destination_route import DestinationRoute
from ai.system_info import get_system_information
from ai.destinations.destination_base import DestinationBase
from ai.prompts import (
    AGENT_TEMPLATE,
    SIMPLE_SUMMARIZE_PROMPT,
    SIMPLE_REFINE_PROMPT,
    SINGLE_LINE_SUMMARIZE_PROMPT,
    REPHRASE_TO_KEYWORDS_TEMPLATE,
    TOOLS_SUFFIX    
)

from utilities.token_helper import simple_get_tokens_for_message


class DocumentsAI(DestinationBase):
    """A document-using AI that uses an LLM to generate responses"""

    def __init__(
        self, destination: Destination, interaction_manager: InteractionManager
    ):
        self.destination = destination
        self.interaction_manager = interaction_manager

        self.llm = get_llm(destination.model_configuration)

        self.create_document_tools()        

        self.agent = initialize_agent(
            self.document_tools,
            self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            human_message_template=AGENT_TEMPLATE,
            agent_kwargs={
                "suffix": TOOLS_SUFFIX,
                "input_variables": [
                    "input",
                    #"agent_chat_history",
                    "agent_scratchpad",
                    "system_information",
                ],
            },
        )

        # Agents should have their own memory (containing past tool runs or other info) that is combined with the conversation memory
        # Combine with the overall conversation memory
        #agent.memory = CombinedMemory(memories=[memory, agent_memory])

        # Set the memory on the agent tools callback so that it can manually add entries
        #self.agent_tools_callback.memory = agent_memory.memory


    def create_document_tools(self):
        self.document_tools = [
            StructuredTool.from_function(       
                name="search_documents",
                func=self.search_loaded_documents,
                description="Good for when you need to search through the loaded documents for an answer to a question.  Use this when the user is referring to any loaded documents in their search for information.",
            ),
            StructuredTool.from_function(
                name="summarize_document",
                func=self.summarize_document,
                description="Useful for summarizing a specific document. Only use this if the user is asking you to summarize a specific document.",
            ),
        ]

    def run(self, input: str):
        
        self.interaction_manager.conversation_token_buffer_memory.chat_memory.add_user_message(input) #.add_message(HumanMessage(input))

        results = self.agent.run(
                input=input,
                system_information=get_system_information(self.interaction_manager.user_location),
                user_name=self.interaction_manager.user_name,
                user_email=self.interaction_manager.user_email,
            )
        
        try:
            # Try loading the result as json (sometimes it doesn't run the tool on its own)
            results = json.loads(results)

            # Find the tool
            for tool in self.document_tools:
                if tool.name.lower() == results["action"].lower():
                    # Run the tool
                    results = tool.func(**results["action_input"])
                    break
        except Exception as e:
            print(f"Error loading json from agent results, {e}")            
            
        print(results)
        self.interaction_manager.conversation_token_buffer_memory.chat_memory.add_ai_message(results) #postgres_chat_message_history.add_message(AIMessage(results))

        return results

    def search_loaded_documents(
        self,
        query: str
    ):
        search_kwargs = {
            "top_k": 20,
            "search_type": SearchType.similarity,
            "interaction_id": self.interaction_manager.interaction_id,
            "collection_id": self.interaction_manager.collection_id,
        }

        # Create the documents class for the retriever
        self.pgvector_retriever = PGVectorRetriever(
            vectorstore=Documents(self.interaction_manager.db_env_location), search_kwargs=search_kwargs
        )

        qa = RetrievalQA.from_chain_type(
            llm=self.llm, chain_type="stuff", retriever=self.pgvector_retriever
        )

        results = qa.run(query=query)

        return results

    # TODO: Replace this summarize with a summarize call when ingesting documents.  Store the summary in the DB for retrieval here.
    def summarize_document(
        self,
        target_document: str,
        query: str,
    ):
        # Create the documents class for the retriever
        documents = Documents(self.interaction_manager.db_env_location)

        with documents.session_context(documents.Session()) as session:
            document_chunks = documents.get_document_chunks_by_document_name(
                session, self.interaction_manager.collection_id, target_document
            )

            # Loop through the found documents, and join them until they fill up as much context as we can
            docs = []
            doc_str = ""
            for doc in document_chunks:
                doc_str += doc.document_text + "\n"
                if (
                    simple_get_tokens_for_message(doc_str) > 2000
                ):  # TODO: Get rid of this magic number
                    docs.append(
                        Document(
                            page_content=doc_str,
                            metadata=json.loads(
                                doc.additional_metadata
                            ),  # Only use the last metadata
                        )
                    )
                    doc_str = ""

            if len(docs) <= 0:
                result = "Sorry, I couldn't find any documents to summarize."
            elif len(docs) == 1:
                result = self.summarize(self.llm, docs)
            else:
                result = self.refine_summarize(self.llm, docs)

            return result

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

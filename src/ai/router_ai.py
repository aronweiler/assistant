import json
import logging
from datetime import datetime
from uuid import uuid4, UUID

from gnews import GNews

from db.database.models import User, Interaction
from db.models.documents import DocumentCollection, Documents
from db.models.conversations import Conversations, SearchType
from db.models.users import Users
from db.models.interactions import Interactions
from db.models.pgvector_retriever import PGVectorRetriever

from langchain_experimental.plan_and_execute import (
    PlanAndExecute,
    load_agent_executor,
    load_chat_planner,
)
from langchain.agents import (
    initialize_agent,
    AgentType,
    AgentExecutor,
    AgentOutputParser,
)
from langchain.chat_models import ChatOpenAI
from langchain.memory import (
    ConversationTokenBufferMemory,
    CombinedMemory,
    ConversationBufferMemory,
    ReadOnlySharedMemory,
)
from langchain.base_language import BaseLanguageModel
from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chains.router.llm_router import LLMRouterChain, RouterOutputParser
from langchain.chains import RetrievalQA, StuffDocumentsChain
from langchain.chains.summarize import load_summarize_chain
from langchain.schema import Document

from langchain.tools import DuckDuckGoSearchRun, StructuredTool
from langchain.chains.base import Chain
from langchain.tools import StructuredTool
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import HumanMessage, AIMessage

from memory.postgres_chat_message_history import PostgresChatMessageHistory
from utilities.openai_utilities import get_openai_api_key
from utilities.token_helper import simple_get_tokens_for_message

from tools.general.time_tool import TimeTool
from tools.weather.weather_tool import WeatherTool
from tools.web.requests_tool import RequestsTool
from tools.web.wikipedia_tool import WikipediaTool
from tools.news.g_news_tool import GNewsTool
from tools.restaurants.yelp_tool import YelpTool

from ai.agent_callback import AgentCallback

# from ai.output_parser import StructuredChatOutputParserWithRetries
from langchain.output_parsers.structured import StructuredOutputParser

from ai.abstract_ai import AbstractAI
from configuration.ai_configuration import AIConfiguration
from ai.prompts import (
    CONVERSATIONAL_PROMPT,
    MEMORY_PROMPT,
    MULTI_PROMPT_ROUTER_TEMPLATE,
    AGENT_TEMPLATE,
    TOOLS_SUFFIX,
    SUMMARIZE_FOR_LABEL_TEMPLATE,
    REPHRASE_TEMPLATE,
    SIMPLE_SUMMARIZE_PROMPT,
    SIMPLE_REFINE_PROMPT,
    SINGLE_LINE_SUMMARIZE_PROMPT,
    REPHRASE_TO_KEYWORDS_TEMPLATE
)


class RouterAI(AbstractAI):
    final_rephrase_prompt = ""
    agent_tools_callback = AgentCallback()
    collection_id = None

    CURRENT_EVENT_TOOLS = [
        StructuredTool.from_function(
            TimeTool().get_time, return_direct=True, callbacks=[agent_tools_callback]
        ),
        StructuredTool.from_function(
            WeatherTool().get_weather, callbacks=[agent_tools_callback]
        ),
        StructuredTool.from_function(
            GNewsTool().get_full_article, callbacks=[agent_tools_callback]
        ),
        StructuredTool.from_function(
            GNewsTool().get_news_by_location, callbacks=[agent_tools_callback]
        ),
        StructuredTool.from_function(
            GNewsTool().get_news, callbacks=[agent_tools_callback]
        ),
        StructuredTool.from_function(
            GNewsTool().get_top_news, callbacks=[agent_tools_callback]
        ),
    ]

    # TBD
    DOCUMENT_TOOLS = [
        
    ]

    INTERNET_TOOLS = [
        StructuredTool.from_function(
            YelpTool().search_businesses, callbacks=[agent_tools_callback]
        ),
        StructuredTool.from_function(
            YelpTool().get_all_business_details, callbacks=[agent_tools_callback]
        ),
        StructuredTool.from_function(
            DuckDuckGoSearchRun()._run, callbacks=[agent_tools_callback]
        ),
        StructuredTool.from_function(
            RequestsTool().search_website, callbacks=[agent_tools_callback]
        ),
        StructuredTool.from_function(
            WikipediaTool().search_wikipedia, callbacks=[agent_tools_callback]
        ),
    ]

    def __init__(self, ai_configuration: AIConfiguration, interaction_id: UUID = None):
        """Create a new RouterAI

        Args:
            ai_configuration (AIConfiguration): AI configuration
            interaction_id (UUID, optional): The interaction ID here is to be passed in by applications that want to switch to or use a specific interaction,
                such as chatbots. Defaults to None.  This can also be configured in the ai configuration section.
        """
        self.ai_configuration = ai_configuration
        self.interactions_helper = Interactions(ai_configuration.db_env_location)

        # Pull the default user
        users = Users(self.ai_configuration.db_env_location)
        with users.session_context(users.Session()) as session:
            user = users.find_user_by_email(
                session,
                email=self.ai_configuration.user_email,
                eager_load=[],
            )

            if user is None:
                raise Exception(
                    f"User with email {self.ai_configuration.user_email} not found."
                )

            self.default_user_id = user.id

        # Do we have an interaction ID in the configuration? (only use it if we have no incoming interaction id)
        if interaction_id is None:
            if self.ai_configuration.interaction_id is not None:
                interaction_id = self.ai_configuration.interaction_id

        with self.interactions_helper.session_context(
            self.interactions_helper.Session()
        ) as session:
            if interaction_id is None:
                # Create a new interaction
                # Get a unique interaction id
                self.interaction_id = uuid4()
                self.interactions_helper.create_interaction(
                    session,
                    self.interaction_id,
                    "Chat: " + str(self.interaction_id),
                    self.default_user_id,
                )
                self.interaction_needs_summary = True
            else:
                # This is using an existing interaction
                self.interaction_id = interaction_id

                # Get the interaction from the db
                interaction = self.interactions_helper.get_interaction(
                    session, self.interaction_id
                )

                if interaction is None:
                    self.interactions_helper.create_interaction(
                        session,
                        self.interaction_id,
                        "Chat: " + str(self.interaction_id),
                        self.default_user_id,
                    )
                    self.interaction_needs_summary = True
                else:
                    # Could still need summary if the interaction was just created
                    self.interaction_needs_summary = interaction.needs_summary

        print(f"Interaction ID: {self.interaction_id}")

        # Initialize the AbstractLLM and dependent AIs
        self.configure()

        self.users = Users(self.ai_configuration.db_env_location)
        self.conversations = Conversations(self.ai_configuration.db_env_location)

        openai_api_key = get_openai_api_key()

        self.llm = ChatOpenAI(
            model=self.ai_configuration.llm_arguments_configuration.model,
            max_retries=self.ai_configuration.llm_arguments_configuration.max_function_limit,
            temperature=self.ai_configuration.llm_arguments_configuration.temperature,
            openai_api_key=openai_api_key,
            max_tokens=self.ai_configuration.llm_arguments_configuration.max_completion_tokens,
            verbose=True,
            # streaming=True,
            # callbacks=[StreamingStdOutCallbackHandler()],
        )

        self.create_chains(self.llm)

    def create_chains(self, llm):
        # Database backed conversation memory
        self.postgres_chat_message_history = PostgresChatMessageHistory(
            self.interaction_id,
            conversations=Conversations(
                self.ai_configuration.llm_arguments_configuration.db_env_location
            ),
        )
        self.conversation_token_buffer_memory = ConversationTokenBufferMemory(
            llm=llm,
            memory_key="chat_history",
            input_key="input",
            chat_memory=self.postgres_chat_message_history,
            max_token_limit=1000,
        )

        # Agent memory
        agent_memory = ConversationTokenBufferMemory(
            llm=llm,
            memory_key="agent_chat_history",
            input_key="input",
            max_token_limit=1000,
        )
        agent_memory.human_prefix
        agent_memory_readonly = ReadOnlySharedMemory(memory=agent_memory)

        # Using the langchain stuff pretty much directly from here: https://python.langchain.com/docs/modules/chains/foundational/router

        self.chains = [
            {
                "name": "conversational",
                "description": "Good for carrying on a conversation with a user, or responding to questions that you already know the answer to. Also use this when an answer to the user's question is contained within the context here (chat history or loaded documents).",
                "chain_or_agent": LLMChain(
                    llm=llm,
                    prompt=CONVERSATIONAL_PROMPT,
                    memory=self.conversation_token_buffer_memory,
                ),
                "function": self.converse,
            },
            {
                "name": "memory",
                "description": "Good for when you may need to remember something from a previous conversation with a user, or some information about a user.",
                "chain_or_agent": LLMChain(
                    llm=llm,
                    prompt=MEMORY_PROMPT,
                    memory=self.conversation_token_buffer_memory,
                ),
                "function": self.remember,
            },
            {
                "name": "current-events",
                "description": "Good for when you need to answer a query about current events, such as weather, news, traffic, movie showtimes, etc.",
                "chain_or_agent": self.get_tool_using_agent(
                    llm,
                    self.conversation_token_buffer_memory,
                    self.CURRENT_EVENT_TOOLS,
                    agent_memory_readonly,
                ),
                "function": self.use_tools,
                # TODO: Look at langchain_experimental for PlanAndExecute to replace this agent
                # "secondary_agent": PlanAndExecute(
                #     planner=load_chat_planner(llm),
                #     executor=load_agent_executor(
                #         llm, self.CURRENT_EVENT_TOOLS, verbose=True
                #     ),
                #     verbose=True,
                # ),
            },
            {
                "name": "internet",
                "description": "Good for when you need to search the internet for an answer or look at a specific website or other web-based resource, which could include things like wikipedia, google, ducduckgo, etc.",
                "chain_or_agent": self.get_tool_using_agent(
                    llm,
                    self.conversation_token_buffer_memory,
                    self.INTERNET_TOOLS,
                    agent_memory_readonly,
                ),
                "function": self.use_tools
            },
            {
                "name": "documents-search",
                "description": "Good for when you need to search through the contents of the loaded documents for an answer to a question.  Use this when the user is referring to any loaded documents in their search for information.",                
                "chain_or_agent": llm,
                "function": self.search_documents,
            },
            {
                "name": "documents-summarize",
                "description": "Only use this if the user specifically asks you to summarize a document.",                
                "chain_or_agent": llm,
                "function": self.summarize_documents,
            },
        ]

        # Put the router chain together
        destinations = [f"{p['name']}: {p['description']}" for p in self.chains]

        destinations_str = "\n".join(destinations)

        router_template = MULTI_PROMPT_ROUTER_TEMPLATE.format(
            destinations=destinations_str
        )

        router_prompt = PromptTemplate(
            template=router_template,
            input_variables=["input", "chat_history", "system_information", "loaded_documents"],
            output_parser=RouterOutputParser(),
        )

        self.router_chain = LLMRouterChain.from_llm(
            llm,
            router_prompt,
            input_keys=["input", "chat_history", "system_information", "loaded_documents"],
        )

    def get_conversation_messages(self):
        return self.conversation_token_buffer_memory.buffer_as_messages

    def get_tool_using_agent(self, llm, memory, tools, agent_memory):
        agent = initialize_agent(
            tools,
            llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            human_message_template=AGENT_TEMPLATE,
            agent_kwargs={
                "suffix": TOOLS_SUFFIX,
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
        agent.memory = CombinedMemory(memories=[memory, agent_memory])

        # Set the memory on the agent tools callback so that it can manually add entries
        self.agent_tools_callback.memory = agent_memory.memory

        return agent    

    def new_agent_action(*args, **kwargs):
        print("AGENT ACTION", args, kwargs, flush=True)

    def query(self, query, user_id=None):
        if user_id is None:
            user_id = self.default_user_id

        # Get the user information
        with self.users.session_context(self.users.Session()) as session:
            current_user = self.users.get_user(
                session, user_id, eager_load=[User.user_settings]
            )

            if self.interaction_needs_summary:
                interaction_summary = self.llm.predict(
                    SUMMARIZE_FOR_LABEL_TEMPLATE.format(query=query)
                )
                self.interactions_helper.update_interaction(
                    session, self.interaction_id, interaction_summary, False
                )
                self.interaction_needs_summary = False

            # Find some related context in the conversation table (might or might not use it)
            self.related_context = self.conversations.search_conversations(
                session, query, SearchType.similarity, top_k=20
            )
            # De-dupe the conversations
            self.related_context = list(
                set([pc.conversation_text for pc in self.related_context])
            )
            self.related_context = "\n".join(self.related_context)

            self.current_human_prefix = f"{current_user.name} ({current_user.email})"

            self.postgres_chat_message_history.user_id = user_id
            self.conversation_token_buffer_memory.human_prefix = (
                self.current_human_prefix
            )

            try:
                # Rephrase the query so that it is stand-alone
                # Use the llm to rephrase, adding in the conversation memory for context
                # query = self.rephrase_query_to_standalone(query, current_user)

                # Use the router chain first
                router_result = self.router_chain(
                    {
                        "input": query,
                        "chat_history": "\n".join(
                            [
                                f"{'AI' if m.type == 'ai' else ''}: {m.content}"
                                for m in self.postgres_chat_message_history.messages[-8:]
                            ]
                        ),
                        "system_information": self.get_system_information(current_user),
                        "loaded_documents": "\n".join(self.get_loaded_documents(self.collection_id))
                    }
                )

                default_chain = LLMChain(
                    llm=self.llm,
                    prompt=CONVERSATIONAL_PROMPT,
                    memory=self.conversation_token_buffer_memory,
                )

                # Route it!

                if (
                    "destination" in router_result
                    and router_result["destination"] is not None
                ):
                    # Get the destination chain
                    destination = next(
                        (
                            c
                            for c in self.chains
                            if c["name"] == router_result["destination"]
                        ),
                        None,
                    )

                    if destination is not None:
                        logging.debug(f"Routing to destination: {destination['name']}")

                        response = destination["function"](
                            destination["chain_or_agent"],
                            # destination["secondary_agent"],
                            query,
                            current_user,
                        )
                    else:
                        logging.warn(
                            f"Destination not found: {router_result['destination']}"
                        )
                        response = self.converse(default_chain, query, current_user)
                else:
                    # Use the default chain
                    response = self.converse(default_chain, query, current_user)

                logging.debug(f"Response from LLM: {response}")

                # General AI returns a string
                return self.final_rephrase(response)
            except Exception as e:
                logging.exception(e)
                return "Sorry, I'm not feeling well right now. Please try again later."

    def final_rephrase(self, response):
        if self.final_rephrase_prompt != "":
            output = self.llm.predict(self.final_rephrase_prompt.format(input=response))
            return output
        else:
            return response

    def converse(self, chain: Chain, query: str, user: User):
        # Find any related conversations
        return chain.run(
            system_prompt=self.ai_configuration.llm_arguments_configuration.system_prompt,
            input=query,
            user_id=user.id,
            user_name=user.name,
            user_email=user.email,
            system_information=self.get_system_information(user),
            context=self.related_context,
            loaded_documents=self.get_loaded_documents(self.collection_id)
        )

    def remember(self, chain: Chain, query: str, user: User):
        # Look up some stuff based on the query
        # Looking into the conversations table for now

        with self.conversations.session_context(
            self.conversations.Session()
        ) as session:
            previous_conversations = self.conversations.search_conversations(
                session,
                conversation_text_search_query=query,
                search_type=SearchType.similarity,
                top_k=100,
                associated_user=user,
            )

            # De-dupe the conversations
            previous_conversations = list(
                set([pc.conversation_text for pc in previous_conversations])
            )

            return chain.run(input=query, context="\n".join(previous_conversations))    

    def use_tools(
        self,
        agent: AgentExecutor,
        query: str,
        user: User,
    ):
        # If there's a CombinedMemory
        if isinstance(agent.memory, CombinedMemory):
            for memory in agent.memory.memories:
                if isinstance(memory, ReadOnlySharedMemory):
                    # The readonly memory is the agent memory
                    memory.memory.human_prefix = self.current_human_prefix
                    # Add the query while I'm in here
                    memory.memory.chat_memory.messages.append(
                        HumanMessage(content=query)
                    )

                    # Extract the last 4 messages from the conversation memory for the secondary agent
                    # chat_history = "\n".join(
                    #     [
                    #         f"{'AI' if m.type == 'ai' else f'{user.name} ({user.email})'}: {m.content}"
                    #         for m in memory.memory.chat_memory.messages[-4:]
                    #     ]
                    # )
                else:
                    memory.human_prefix = self.current_human_prefix
        else:
            agent.memory.human_prefix = self.current_human_prefix

        try:
            results = agent.run(
                input=query,
                system_information=self.get_system_information(user),
                user_name=user.name,
                user_email=user.email,
            )
        except Exception as e:
            logging.exception(e)
            return "Sorry, the agent couldn't process the request.  Please try again later."

        # Put the run of the secondary agent back in when it doesn't suck
        # question_answered = self.llm.predict(
        #     SECONDARY_AGENT_ROUTER_TEMPLATE.format(
        #         response=results,
        #         system_information=self.get_system_information(user),
        #         chat_history=chat_history,
        #     )
        # )
        # if question_answered.lower() != "yes":
        #     results = secondary_agent.run(question_answered)

        # Try to load the result into a json object
        # If it fails, just return the string
        try:
            results = json.loads(results)
        except:
            return results

        # Find the tool
        for tool in self.INTERNET_TOOLS + self.CURRENT_EVENT_TOOLS:
            if tool.name.lower() == results["action"].lower():
                # Run the tool
                return tool.run(**results["action_input"])

        return results

    def search_documents(
        self,
        llm: BaseLanguageModel,
        query: str,
        user: User,
    ):
        rephrased_query = self.rephrase_query_to_search_keywords(query, user)
        #rephrased_query = self.rephrase_query_to_standalone(query, user)

        # Create the documents class for the retriever
        documents = Documents(self.ai_configuration.db_env_location)
        self.pgvector_retriever = PGVectorRetriever(vectorstore=documents)

        qa = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=self.pgvector_retriever,
        )

        # Set the search kwargs for my custom retriever
        # TODO: Replace "general" with the actual collection name
        search_kwargs = {
            "top_k": 20,
            "search_type": SearchType.similarity,
            "interaction_id": self.interaction_id,
            "collection_id": self.collection_id,
        }
        self.pgvector_retriever.search_kwargs = search_kwargs

        results = qa.run(query=rephrased_query)

        self.postgres_chat_message_history.add_user_message(query)
        self.postgres_chat_message_history.add_ai_message(results)

        return results
    
    # TODO: Replace this summarize with a summarize call when ingesting documents.  Store the summary in the DB for retrieval here.
    def summarize_documents(
        self,
        llm: BaseLanguageModel,
        query: str,
        user: User,
    ):
        query = self.rephrase_query_to_standalone(query, user)

        # Create the documents class for the retriever
        documents = Documents(self.ai_configuration.db_env_location)
        self.pgvector_retriever = PGVectorRetriever(vectorstore=documents)

        with documents.session_context(documents.Session()) as session:
            document_chunks = documents.get_document_chunks_by_collection_id(session, self.collection_id)

            # Loop through the found documents, and join them until they fill up as much context as we can
            docs = []
            doc_str = ''
            for doc in document_chunks:
                doc_str += doc.document_text + '\n'
                if simple_get_tokens_for_message(doc_str) > 2000: # TODO: Get rid of this magic number
                    docs.append(Document(
                        page_content=doc_str,
                        metadata=json.loads(doc.additional_metadata) # Only use the last metadata
                    ))
                    doc_str = ''

            if len(docs) <= 0:
                result = "Sorry, I couldn't find any documents to summarize."            
            elif len(docs) == 1:
                result = self.summarize(llm, docs)
            else:
                result = self.refine_summarize(llm, docs)

            # Add the messages manually to the conversation memory
            self.postgres_chat_message_history.add_user_message(query)
            self.postgres_chat_message_history.add_ai_message(result)

            return result

    def refine_summarize(self, llm, docs):       
        chain = load_summarize_chain(
            llm=llm,
            chain_type="refine",
            question_prompt=SIMPLE_SUMMARIZE_PROMPT,
            refine_prompt=SIMPLE_REFINE_PROMPT,
            return_intermediate_steps=True,
            input_key="input_documents",
            output_key="output_text"
        )
        
        result = chain({"input_documents": docs}, return_only_outputs=True)

        return result["output_text"]
    
    def summarize(self, llm, docs):       
        llm_chain = LLMChain(llm=llm, prompt=SINGLE_LINE_SUMMARIZE_PROMPT)

        stuff_chain = StuffDocumentsChain(llm_chain=llm_chain, document_variable_name="text")
                                          
        return stuff_chain.run(docs)
    
    def rephrase_query_to_standalone(self, query, user):
        # Rephrase the query so that it is stand-alone
        # Use the llm to rephrase, adding in the conversation memory for context
        rephrase_results = self.llm.predict(
            REPHRASE_TEMPLATE.format(
                input=query,
                chat_history="\n".join(
                    [
                        f"{'AI' if m.type == 'ai' else f'{user.name} ({user.email})'}: {m.content}"
                        for m in self.postgres_chat_message_history.messages[-16:]
                    ]
                ),
                system_information=self.get_system_information(user),
                user_name=user.name,
                user_email=user.email,
                loaded_documents="\n".join(self.get_loaded_documents(self.collection_id))
            )
        )

        return rephrase_results
    
    def rephrase_query_to_search_keywords(self, query, user):
        # Rephrase the query so that it is stand-alone
        # Use the llm to rephrase, adding in the conversation memory for context
        rephrase_results = self.llm.predict(
            REPHRASE_TO_KEYWORDS_TEMPLATE.format(
                input=query,
                chat_history="\n".join(
                    [
                        f"{'AI' if m.type == 'ai' else f'{user.name} ({user.email})'}: {m.content}"
                        for m in self.postgres_chat_message_history.messages[-16:]
                    ]
                ),
                system_information=self.get_system_information(user),
                user_name=user.name,
                user_email=user.email,
                loaded_documents="\n".join(self.get_loaded_documents(self.collection_id))
            )
        )

        return rephrase_results
    
    def get_loaded_documents(self, collection_id):
        documents = Documents(self.ai_configuration.db_env_location)

        with documents.session_context(documents.Session()) as session:
            docs = documents.get_collection_file_names(session, collection_id)
            return [d.document_name for d in docs]

    def get_system_information(self, user: User):
        return f"Current Date/Time: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}. Current Time Zone: {datetime.now().astimezone().tzinfo}.  Current Location: {user.location}"

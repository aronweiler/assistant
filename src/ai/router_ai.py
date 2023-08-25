import json
import logging
from datetime import datetime
from uuid import uuid4

from gnews import GNews

from db.database.models import User
from db.models.conversations import Conversations, SearchType
from db.models.users import Users

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
from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chains.router.llm_router import LLMRouterChain, RouterOutputParser

from langchain.tools import DuckDuckGoSearchRun, StructuredTool
from langchain.chains.base import Chain
from langchain.tools import StructuredTool
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import HumanMessage

from memory.postgres_chat_message_history import PostgresChatMessageHistory
from utilities.openai_utilities import get_openai_api_key

from tools.general.time_tool import TimeTool
from tools.weather.weather_tool import WeatherTool
from tools.web.requests_tool import RequestsTool
from tools.web.wikipedia_tool import WikipediaTool
from tools.news.g_news_tool import GNewsTool
from tools.restaurants.yelp_tool import YelpTool

from ai.agent_callback import AgentCallback
from ai.output_parser import StructuredChatOutputParserWithRetries

from ai.abstract_ai import AbstractAI
from configuration.ai_configuration import AIConfiguration
from ai.prompts import (
    CONVERSATIONAL_PROMPT,
    MEMORY_PROMPT,
    MULTI_PROMPT_ROUTER_TEMPLATE,
    AGENT_TEMPLATE,
    TOOLS_SUFFIX,
)


class RouterAI(AbstractAI):
    final_rephrase_prompt = ''
    agent_tools_callback = AgentCallback()

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

    def __init__(self, ai_configuration: AIConfiguration):
        self.ai_configuration = ai_configuration

        # Get a unique interaction id
        self.interaction_id = uuid4()
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
                "description": "Good for carrying on a conversation with a user, or responding to questions that you already know the answer to.",
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
                "chain_or_agent": self.get_agent(
                    llm,
                    self.conversation_token_buffer_memory,
                    self.CURRENT_EVENT_TOOLS,
                    agent_memory_readonly,
                ),
                "function": self.use_tools,
            },
            {
                "name": "internet",
                "description": "Good for when you need to search the internet for an answer or look at a specific website or other web-based resource, which could include things like wikipedia, google, ducduckgo, etc.",
                "chain_or_agent": self.get_agent(
                    llm,
                    self.conversation_token_buffer_memory,
                    self.INTERNET_TOOLS,
                    agent_memory_readonly,
                ),
                "function": self.use_tools,
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
            input_variables=["input", "chat_history", "system_information"],
            output_parser=RouterOutputParser(),
        )

        self.router_chain = LLMRouterChain.from_llm(
            llm,
            router_prompt,
            input_keys=["input", "chat_history", "system_information"],
        )

    def get_conversation(self):
        return self.conversation_token_buffer_memory.buffer

    def get_agent(self, llm, memory, tools, agent_memory):
        # Use my custom parser because ChatGPT occasionally returns junk
        output_parser = StructuredChatOutputParserWithRetries()

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
                    "system_information"
                ],
                "output_parser": output_parser,
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

    def query(self, query, user_id):

        # Get the user information
        with self.users.session_context(self.users.Session()) as session:
            current_user = self.users.get_user(
                session, user_id, eager_load=[User.user_settings]
            )

            # Find some related context in the conversation table (might or might not use it)
            self.related_context = self.conversations.search_conversations(session, query, SearchType.similarity, top_k=20)
            # De-dupe the conversations
            self.related_context = list(
                set([pc.conversation_text for pc in self.related_context])
            )
            self.related_context = "\n".join(self.related_context)

            self.current_user_id = user_id
            self.current_human_prefix = f"{current_user.name} ({current_user.email})"

            self.postgres_chat_message_history.user_id = user_id
            self.conversation_token_buffer_memory.human_prefix = (
                self.current_human_prefix
            )

            try:
                # Use the router chain first (why does this use a dictionary when the other calls are all named inputs?? no idea)
                router_result = self.router_chain(
                    {
                        "input": query,
                        "chat_history": "\n".join(
                            [
                                f"{'AI' if m.type == 'ai' else ''}: {m.content}"
                                for m in self.postgres_chat_message_history.messages
                            ]
                        ),
                        "system_information": self.get_system_information(current_user),
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
                            destination["chain_or_agent"], query, current_user
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
        if self.final_rephrase_prompt != '':
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
            context=self.related_context
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

            return chain.run(
                input=query,
                context="\n".join(previous_conversations)
            )

    def use_tools(self, agent: AgentExecutor, query: str, user: User):

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

    def get_system_information(self, user: User):
        return f"Current Date/Time: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}. Current Time Zone: {datetime.now().astimezone().tzinfo}.  Current Location: {user.location}"

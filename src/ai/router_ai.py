from uuid import uuid4
from langchain.memory import ConversationTokenBufferMemory
from langchain.chains.router import MultiPromptChain
from langchain.llms import OpenAI
from langchain.chains import ConversationChain
from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chains.router.llm_router import LLMRouterChain, RouterOutputParser
from langchain.chains.router.multi_prompt_prompt import MULTI_PROMPT_ROUTER_TEMPLATE

from langchain.chains.base import Chain

from llms.memory.postgres_chat_message_history import PostgresChatMessageHistory

from ai.abstract_ai import AbstractAI
from configuration.ai_configuration import AIConfiguration
from ai.prompts import CONVERSATIONAL_PROMPT, MEMORY_PROMPT

from llms.open_ai.utilities.open_ai_utilities import get_openai_api_key
import logging
from datetime import datetime

from db.database.models import User

from db.models.conversations import Conversations, SearchType
from db.models.users import Users

from langchain.chat_models import ChatOpenAI


class RouterAI(AbstractAI):
    def __init__(self, ai_configuration: AIConfiguration):
        self.ai_configuration = ai_configuration

        # Initialize the AbstractLLM and dependent AIs
        self.configure()

        self.users = Users(self.ai_configuration.db_env_location)
        self.conversations = Conversations(self.ai_configuration.db_env_location)

        openai_api_key = get_openai_api_key()

        self.llm = ChatOpenAI(
            model=self.ai_configuration.llm_configuration.llm_arguments_configuration.model,
            max_retries=self.ai_configuration.llm_configuration.llm_arguments_configuration.max_function_limit,
            temperature=self.ai_configuration.llm_configuration.llm_arguments_configuration.temperature,
            openai_api_key=openai_api_key,
            max_tokens=self.ai_configuration.llm_configuration.llm_arguments_configuration.max_completion_tokens,
            verbose=True,
            # streaming=True,
            # callbacks=[StreamingStdOutCallbackHandler()],
        )

        self.create_chains(self.llm)

    def create_chains(self, llm):
        # Database backed conversation memory
        self.postgres_chat_message_history = PostgresChatMessageHistory(
            interaction_id=uuid4(),
            conversations=Conversations(
                self.ai_configuration.llm_configuration.llm_arguments_configuration.db_env_location
            ),
        )
        self.conversation_token_buffer_memory = ConversationTokenBufferMemory(
            llm=llm,
            memory_key="chat_history",
            input_key="input",
            max_token_limit=30,
            chat_memory=self.postgres_chat_message_history,
        )

        # Using the langchain stuff pretty much directly from here: https://python.langchain.com/docs/modules/chains/foundational/router

        self.chains = [
            {
                "name": "conversational",
                "description": "Good for carrying on a conversation with a user",
                "prompt": CONVERSATIONAL_PROMPT,  # Maybe for later
                "chain": LLMChain(
                    llm=llm,
                    prompt=CONVERSATIONAL_PROMPT,
                    memory=self.conversation_token_buffer_memory,
                ),
                "function": self.converse,
            },
            {
                "name": "memory",
                "description": "Good for when you may need to remember something from a previous conversation with a user, or some information about a user",
                "prompt": MEMORY_PROMPT,
                "chain": LLMChain(llm=llm, prompt=MEMORY_PROMPT),
                "function": self.remember,
            }
        ]

        # Put the router chain together
        destinations = [f"{p['name']}: {p['description']}" for p in self.chains]

        destinations_str = "\n".join(destinations)

        router_template = MULTI_PROMPT_ROUTER_TEMPLATE.format(
            destinations=destinations_str
        )

        router_prompt = PromptTemplate(
            template=router_template,
            input_variables=["input"],
            output_parser=RouterOutputParser(),
        )

        self.router_chain = LLMRouterChain.from_llm(llm, router_prompt)

    def query(self, query, user_id):
        # Get the user information
        with self.users.session_context(self.users.Session()) as session:
            current_user = self.users.get_user(
                session, user_id, eager_load=[User.user_settings]
            )

            self.postgres_chat_message_history.user_id = user_id

            try:
                # Use the router chain first
                router_result = self.router_chain(query)

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
                            destination["chain"], query, current_user
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
                return response
            except Exception as e:
                logging.exception(e)
                return "Sorry, I'm not feeling well right now. Please try again later."

    def converse(self, chain: Chain, query: str, user: User):
        system_information = f"Current Date/Time: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}. Current Time Zone: {datetime.now().astimezone().tzinfo}"

        return chain.run(
            system_prompt=self.ai_configuration.llm_configuration.llm_arguments_configuration.system_prompt,
            input=query,
            user_id=user.id,
            user_name=user.name,
            user_email=user.email,
            system_information=system_information,
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
                context="\n".join(previous_conversations),
            )

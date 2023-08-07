import logging

from langchain import PromptTemplate
from langchain.chains import LLMChain as llm_chain
from langchain.memory import ConversationTokenBufferMemory
import json
from uuid import uuid4
import logging
from datetime import datetime
from typing import Union, List, Dict
from tools.results.summarize_result import SummarizeResult

from langchain.llms import OpenAI, LlamaCpp
from langchain.chat_models import ChatOpenAI
from langchain.callbacks import StreamingStdOutCallbackHandler


from utilities.pretty_print import pretty_print_conversation
from utilities.token_helper import (
    num_tokens_from_messages,
    simple_get_tokens_for_message,
)


from configuration.llm_arguments_configuration import LLMArgumentsConfiguration

from llms.abstract_llm import AbstractLLM
from llms.llm_result import LLMResult
from llms.open_ai.utilities.tool_loader import (
    load_tool_from_config,
    load_tool_from_instance,
)
from llms.open_ai.utilities.chat_completion import OpenAIChatCompletion
from llms.open_ai.utilities.open_ai_utilities import get_openai_api_key
from llms.open_ai.utilities.function_caller import call_function

from tools.general.list_tool import ListTool
from tools.general.tool_recommender import ToolRecommender

from db.database.models import User
from db.models.vector_database import VectorDatabase
from llms.memory.conversation_entity_memory import CustomConversationEntityMemory

from langchain.memory import (
    ConversationKGMemory,
    CombinedMemory,
)

from llms.memory.postgres_chat_message_history import PostgresChatMessageHistory
from llms.memory.postgres_entity_store import PostgreSQLEntityStore

from db.models.conversations import Conversations
from db.models.users import Users

from llms.memory.prompts import ENTITY_EXTRACTION_PROMPT, DEFAULT_PROMPT


class LangChainLLMChain(AbstractLLM):
    def __init__(self, llm_arguments_configuration: LLMArgumentsConfiguration):
        self.llm_arguments_configuration = llm_arguments_configuration

        openai_api_key = get_openai_api_key()

        self.users = Users(llm_arguments_configuration.db_env_location)

        llm = ChatOpenAI(
            model=llm_arguments_configuration.model,
            max_retries=llm_arguments_configuration.max_function_limit,
            temperature=llm_arguments_configuration.temperature,
            openai_api_key=openai_api_key,
            max_tokens=llm_arguments_configuration.max_completion_tokens,
            verbose=True,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
        )

        # Using a few different types of memory here

        # Conversation knowledge graph memory
        # conversation_knowledge_graph_memory = ConversationKGMemory(
        #     llm=llm, memory_key="conversation_knowledge_graph", input_key="input"
        # )

        # Conversation token buffer memory backed by the Conversations model (could be database- it is right now)
        self.postgres_chat_message_history = PostgresChatMessageHistory(
            interaction_id=uuid4(),
            conversations=Conversations(llm_arguments_configuration.db_env_location),
        )
        conversation_token_buffer_memory = ConversationTokenBufferMemory(
            llm=llm,
            memory_key="chat_history",
            input_key="input",
            max_token_limit=30,
            chat_memory=self.postgres_chat_message_history,
        )

        # Entity memory with a database backing
        connection_string = VectorDatabase.get_connection_string(
            llm_arguments_configuration.db_env_location
        )
        self.postgres_entity_store = PostgreSQLEntityStore(
            llm=llm,
            db_url=connection_string,
            chat_memory=self.postgres_chat_message_history,
        )
        self.db_store_entity_memory = CustomConversationEntityMemory(
            llm=llm,
            entity_store=self.postgres_entity_store,
            memory_key="entities",
            input_key="input",
            entity_extraction_prompt=ENTITY_EXTRACTION_PROMPT,
        )

        combined_memory = CombinedMemory(
            memories=[
                self.db_store_entity_memory,
                #conversation_knowledge_graph_memory,
                conversation_token_buffer_memory,
            ]
        )

        self.chain = llm_chain(
            llm=llm, verbose=True, memory=combined_memory, prompt=DEFAULT_PROMPT
        )

    def query(self, input, user_id, user_name, user_email, system_information):
        num_tokens = 0

        self.postgres_chat_message_history.user_id = user_id

        if isinstance(input, str):
            # If the input is a single string
            num_tokens = simple_get_tokens_for_message(input)
        elif isinstance(input, list):
            # If the input is a list of strings
            for string in input:
                num_tokens += num_tokens_from_messages(string)

        logging.debug(f"LLMChain query has {num_tokens} tokens")

        self.db_store_entity_memory.human_prefix = user_name
        self.postgres_entity_store.human_prefix = user_name

        result = self.chain(
            inputs={
                "input": input,
                "user_name": user_name,
                "user_email": user_email,
                "system_information": system_information,
                "system_prompt": self.llm_arguments_configuration.system_prompt,
                "human_prefix": f"{user_name} ({user_email})",
            }
        )  # [-1]['content']) # For messages

        return LLMResult(result, result["text"], False)

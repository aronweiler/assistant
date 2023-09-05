import logging
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
)
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

from ai.interactions.interaction_manager import InteractionManager
from ai.llm_helper import get_llm
from ai.system_info import get_system_information
from ai.destination_route import DestinationRoute
from ai.system_info import get_system_information
from ai.destinations.destination_base import DestinationBase
from ai.callbacks.token_management_callback import TokenManagementCallbackHandler
from ai.callbacks.agent_callback import AgentCallback

from tools.general.time_tool import TimeTool
from tools.weather.weather_tool import WeatherTool
from tools.news.g_news_tool import GNewsTool

from ai.prompts import (
    AGENT_TEMPLATE,
    TOOLS_SUFFIX,
)


class CurrentEventsAI(DestinationBase):
    """A current events AI that uses various APIs to generate responses"""

    def __init__(
        self,
        destination: Destination,
        interaction_id: int,
        user_email: str,
        db_env_location: str,
        streaming: bool = False,
    ):
        self.destination = destination        

        self.token_management_handler = TokenManagementCallbackHandler()
        self.agent_callback = AgentCallback()

        self.llm = get_llm(
            destination.model_configuration,
            callbacks=[self.token_management_handler],
            tags=["current-events"],
            streaming=streaming,
        )

        self.interaction_manager = InteractionManager(
            interaction_id,
            user_email,
            self.llm,
            db_env_location,
            destination.model_configuration.max_conversation_history_tokens,
        )

        self.load_tools()

        self.agent = initialize_agent(
            self.current_events_tools,
            self.llm,
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

    def load_tools(self):
        """Loads the tools for the current events AI"""
        self.current_events_tools = [
            StructuredTool.from_function(
                TimeTool().get_time, return_direct=True, callbacks=[self.agent_callback]
            ),
            StructuredTool.from_function(
                WeatherTool().get_weather, callbacks=[self.agent_callback]
            ),
            StructuredTool.from_function(
                GNewsTool().get_full_article, callbacks=[self.agent_callback]
            ),
            StructuredTool.from_function(
                GNewsTool().get_news_by_location, callbacks=[self.agent_callback]
            ),
            StructuredTool.from_function(
                GNewsTool().get_news, callbacks=[self.agent_callback]
            ),
            StructuredTool.from_function(
                GNewsTool().get_top_news, callbacks=[self.agent_callback]
            ),
        ]

    def run(self, input: str, collection_id: str = None, llm_callbacks: list = [], agent_callbacks: list = []):
        self.interaction_manager.collection_id = collection_id
        results = self.agent.run(
            input=input,
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
        )

        self.interaction_manager.conversation_token_buffer_memory.chat_memory.add_ai_message(
            results
        )  # postgres_chat_message_history.add_message(AIMessage(results))

        return results
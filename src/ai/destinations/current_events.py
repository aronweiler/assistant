import logging

from langchain.agents.structured_chat.output_parser import (
    StructuredChatOutputParserWithRetries,
)
from langchain.memory.readonly import ReadOnlySharedMemory
from langchain.agents import (
    initialize_agent,
    AgentType,
)

from langchain.tools import StructuredTool

from src.configuration.assistant_configuration import Destination

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm, get_prompt
from src.ai.system_info import get_system_information
from src.ai.system_info import get_system_information
from src.ai.destinations.destination_base import DestinationBase
from src.ai.callbacks.token_management_callback import TokenManagementCallbackHandler
from src.ai.callbacks.agent_callback import AgentCallback

from src.tools.general.time_tool import TimeTool
from src.tools.weather.weather_tool import WeatherTool
from src.tools.news.g_news_tool import GNewsTool


class CurrentEventsAI(DestinationBase):
    """A current events AI that uses various APIs to generate responses"""

    def __init__(
        self,
        destination: Destination,
        interaction_id: int,
        user_email: str,
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
            destination.model_configuration.max_conversation_history_tokens,
        )

        self.load_tools()

        self.agent = self.create_agent()

    def create_agent(self, agent_timeout: int = 120):
        logging.debug("Setting human message template")
        human_message_template = get_prompt(
            self.destination.model_configuration.llm_type, "AGENT_TEMPLATE"
        )

        logging.debug("Setting memory")
        memory = ReadOnlySharedMemory(
            memory=self.interaction_manager.conversation_token_buffer_memory
        )

        logging.debug("Setting suffix")
        suffix = get_prompt(
            self.destination.model_configuration.llm_type, "TOOLS_SUFFIX"
        )

        logging.debug("Setting format instructions")
        format_instructions = get_prompt(
            self.destination.model_configuration.llm_type,
            "TOOLS_FORMAT_INSTRUCTIONS",
        )

        # This is a problem with langchain right now- hopefully it resolves soon, because the StructuredChatOutputParserWithRetries is crap without the llm
        try:
            output_parser = StructuredChatOutputParserWithRetries.from_llm(llm=self.llm)
        except Exception as e:
            logging.error(f"Could not create output parser: {e}")
            logging.warning("Falling back to default output parser")
            output_parser = StructuredChatOutputParserWithRetries()

        logging.debug("Setting agent kwargs")
        agent_kwargs = {
            "suffix": suffix,
            "format_instructions": format_instructions,
            "output_parser": output_parser,
            "input_variables": [
                "input",
                "loaded_documents",
                "chat_history",
                "agent_scratchpad",
                "system_information",
            ],
            "verbose": True,
        }

        logging.debug(f"Creating agent with kwargs: {agent_kwargs}")
        agent = initialize_agent(
            tools=self.current_events_tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            human_message_template=human_message_template,
            memory=memory,
            agent_kwargs=agent_kwargs,
            max_execution_time=agent_timeout,
            early_stopping_method="generate",  # try to generate a response if it times out
        )

        return agent

    def load_tools(self):
        """Loads the tools for the current events AI"""
        self.current_events_tools = [
            StructuredTool.from_function(
                TimeTool().get_time, callbacks=[self.agent_callback]
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

    def run(
        self,
        input: str,
        collection_id: str = None,
        llm_callbacks: list = [],
        agent_callbacks: list = [],
        kwargs: dict = {},
    ):
        self.interaction_manager.collection_id = collection_id
        self.interaction_manager.tool_kwargs = kwargs
        
        results = self.agent.run(
            input=input,
            system_information=get_system_information(
                self.interaction_manager.user_location
            ),
            user_name=self.interaction_manager.user_name,
            user_email=self.interaction_manager.user_email,
            loaded_documents="",
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

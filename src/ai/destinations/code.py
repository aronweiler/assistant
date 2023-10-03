import logging
import json

from langchain.agents.structured_chat.output_parser import (
    StructuredChatOutputParserWithRetries,
)
from langchain.tools import StructuredTool
from langchain.agents import (
    initialize_agent,
    AgentType,
)

from src.configuration.assistant_configuration import Destination

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm, get_prompt
from src.ai.system_info import get_system_information
from src.ai.system_info import get_system_information
from src.ai.destinations.destination_base import DestinationBase
from src.ai.callbacks.token_management_callback import TokenManagementCallbackHandler
from src.ai.callbacks.agent_callback import AgentCallback

from src.tools.documents.document_tool import DocumentTool
from src.tools.code.code_tool import CodeTool

from src.ai.agents.code.stubbing_agent import Stubber


class CodeAI(DestinationBase):
    """A document-using AI that contains logic and tools specific to working with code"""

    def __init__(
        self,
        destination: Destination,
        interaction_id: int,
        user_email: str,
        streaming: bool = False,
    ):
        self.destination = destination

        self.agent_callback = AgentCallback()
        self.token_management_handler = TokenManagementCallbackHandler()

        self.llm = get_llm(
            destination.model_configuration,
            callbacks=[self.token_management_handler],
            tags=["code"],
            streaming=streaming,
        )

        self.interaction_manager = InteractionManager(
            interaction_id,
            user_email,
            self.llm,
            destination.model_configuration.max_conversation_history_tokens,
        )

        self.document_tool = DocumentTool(
            configuration=self.destination,
            interaction_manager=self.interaction_manager,
            llm=self.llm,
        )
        self.code_tool = CodeTool(
            configuration=self.destination,
            interaction_manager=self.interaction_manager,
            llm=self.llm,
        )
        self.stubber = Stubber(
            code_tool=self.code_tool,
            document_tool=self.document_tool,
            callbacks=[self.agent_callback],
            interaction_manager=self.interaction_manager,
        )

        self.create_code_tools(self.document_tool, self.code_tool, self.stubber)

        # This is a problem with langchain right now- hopefully it resolves soon, because the StructuredChatOutputParserWithRetries is crap without the llm
        try:
            output_parser = StructuredChatOutputParserWithRetries.from_llm(llm=self.llm)
        except Exception as e:
            logging.error(f"Could not create output parser: {e}")
            logging.warning("Falling back to default output parser")
            output_parser = StructuredChatOutputParserWithRetries()

        self.agent = initialize_agent(
            tools=self.code_tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            human_message_template=get_prompt(
                self.destination.model_configuration.llm_type, "AGENT_TEMPLATE"
            ),
            agent_kwargs={
                "suffix": get_prompt(
                    self.destination.model_configuration.llm_type, "TOOLS_SUFFIX"
                ),
                "format_instructions": get_prompt(
                    self.destination.model_configuration.llm_type,
                    "TOOLS_FORMAT_INSTRUCTIONS",
                ),
                "output_parser": output_parser,
                "input_variables": [
                    "input",
                    "loaded_documents",
                    "chat_history",
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

    def create_code_tools(
        self, document_tool: DocumentTool, code_tool: CodeTool, stubber: Stubber
    ):
        self.code_tools = [
            StructuredTool.from_function(
                func=document_tool.search_loaded_documents, callbacks=[self.agent_callback]
            ),
            StructuredTool.from_function(
                func=document_tool.summarize_topic,
                callbacks=[self.agent_callback],
                return_direct=True,
            ),
            StructuredTool.from_function(
                func=document_tool.list_documents,
                callbacks=[self.agent_callback],
                return_direct=True,
            ),
            StructuredTool.from_function(
                func=code_tool.code_details, callbacks=[self.agent_callback]
            ),
            StructuredTool.from_function(
                func=code_tool.code_structure, callbacks=[self.agent_callback]
            ),
            StructuredTool.from_function(
                func=code_tool.create_stub_code,
                callbacks=[self.agent_callback],
                return_direct=True,
            ),
            StructuredTool.from_function(
                func=code_tool.get_pretty_dependency_graph,
                callbacks=[self.agent_callback],
                return_direct=True,
            ),
            StructuredTool.from_function(
                func=stubber.create_stubs,
                callbacks=[self.agent_callback],
                return_direct=True,
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
        rephrased_input = self.rephrase_query_to_standalone(input)

        results = self.agent.run(
            input=rephrased_input,
            system_information=get_system_information(
                self.interaction_manager.user_location
            ),
            user_name=self.interaction_manager.user_name,
            user_email=self.interaction_manager.user_email,
            loaded_documents="\n".join(
                self.interaction_manager.get_loaded_documents_for_reference()
            ),
            chat_history="\n".join(
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
            for tool in self.code_tools:
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

    def rephrase_query_to_standalone(self, query):
        # Rephrase the query so that it is stand-alone
        # Use the llm to rephrase, adding in the conversation memory for context
        rephrase_results = self.llm.predict(
            get_prompt(
                self.destination.model_configuration.llm_type, "REPHRASE_TEMPLATE"
            ).format(
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

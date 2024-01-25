from langchain.base_language import BaseLanguageModel
from langchain.chains.llm import LLMChain
from langchain.memory.readonly import ReadOnlySharedMemory
from langchain.memory.token_buffer import ConversationTokenBufferMemory

from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.llm_helper import get_tool_llm
from src.ai.system_info import get_system_information
from src.ai.tools.tool_registry import register_tool


class LLMTool:
    def __init__(
        self,
        configuration,
        conversation_manager: ConversationManager,
        llm_callbacks: list = [],
    ):
        self.configuration = configuration
        self.conversation_manager = conversation_manager
        self.llm_callbacks = llm_callbacks

    # @register_tool(
    #     description="Analyze results of another query or queries.",
    #     additional_instructions="This tool is useful for when you want to combine data you have gathered, or just take a moment to think about things.  IMPORTANT: This tool does not have access to documents, or any data outside of what you pass in the 'data_to_analyze' argument.",
    # )
    def analyze_with_llm(self, query: str, data_to_analyze: str):
        """Uses an LLM to answer a query.  This is useful for when you want to just generate a response from an LLM with the given query."""

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.analyze_with_llm.__name__,
            streaming=True,
            model_kwargs={
                "frequency_penalty": 0.7,
                "presence_penalty": 0.6,
            },
            # callbacks=self.conversation_manager.agent_callbacks,
        )

        uses_conversation_history = self.configuration["tool_configurations"][
            self.analyze_with_llm.__name__
        ]["model_configuration"]["uses_conversation_history"]
        max_token_limit = self.configuration["tool_configurations"][
            self.analyze_with_llm.__name__
        ]["model_configuration"]["max_conversation_history_tokens"]

        if not uses_conversation_history:
            memory = None
        else:
            token_memory = ConversationTokenBufferMemory(
                llm=llm,
                memory_key="chat_history",
                input_key="input",
                max_token_limit=max_token_limit,
            )

            # This dumbass shit is due to a miss on langchain's part
            for i in range(
                0,
                len(
                    self.conversation_manager.conversation_token_buffer_memory.buffer_as_messages
                ),
                2,
            ):
                message1 = self.conversation_manager.conversation_token_buffer_memory.buffer_as_messages[
                    i
                ]
                message2 = self.conversation_manager.conversation_token_buffer_memory.buffer_as_messages[
                    i + 1
                ]

                token_memory.save_context(
                    inputs={"input": message1.content},
                    outputs={"output": message2.content},
                )

            memory = ReadOnlySharedMemory(memory=token_memory)

        self.chain = LLMChain(
            llm=llm,
            prompt=self.conversation_manager.prompt_manager.get_prompt_by_category_and_name(
                "conversational_prompts", "CONVERSATIONAL_PROMPT"
            ),
            memory=memory,
        )

        return self.chain.run(
            system_prompt=f"You are a friendly AI agent who's purpose it is to answer the user's query. Do your best to answer given the available data, and your own knowledge.  If you don't know the answer, don't make anything up, just say you don't know.",
            input=query,
            user_name=self.conversation_manager.user_name,
            user_email=self.conversation_manager.user_email,
            system_information=get_system_information(
                self.conversation_manager.user_location
            ),
            context=data_to_analyze,
            loaded_documents="\n".join(
                self.conversation_manager.get_loaded_documents_for_display()
            ),
            # callbacks=self.llm_callbacks,
        )

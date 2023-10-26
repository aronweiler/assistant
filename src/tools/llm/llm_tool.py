from langchain.base_language import BaseLanguageModel
from langchain.chains.llm import LLMChain
from langchain.memory.readonly import ReadOnlySharedMemory

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_tool_llm
from src.ai.system_info import get_system_information


class LLMTool:
    def __init__(
        self,
        configuration,
        interaction_manager: InteractionManager,
        llm_callbacks: list = [],
    ):
        self.configuration = configuration
        self.interaction_manager = interaction_manager
        self.llm_callbacks = llm_callbacks


    def analyze_with_llm(self, query: str, data_to_analyze: str):
        """Uses an LLM to answer a query.  This is useful for when you want to just generate a response from an LLM with the given query."""

        memory = ReadOnlySharedMemory(
            memory=self.interaction_manager.conversation_token_buffer_memory
        )

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.analyze_with_llm.__name__
        )

        self.chain = LLMChain(
            llm=llm,
            prompt=self.interaction_manager.prompt_manager.get_prompt(
                "conversational", "CONVERSATIONAL_PROMPT"
            ),
            memory=memory,
        )

        return self.chain.run(
            system_prompt=f"You are a friendly AI agent who's purpose it is to answer the user's query. Do your best to answer given the available data, and your own knowledge.  If you don't know the answer, don't make anything up, just say you don't know.",
            input=query,
            user_name=self.interaction_manager.user_name,
            user_email=self.interaction_manager.user_email,
            system_information=get_system_information(
                self.interaction_manager.user_location
            ),
            context=data_to_analyze,
            loaded_documents="\n".join(
                self.interaction_manager.get_loaded_documents_for_display()
            ),
            callbacks=self.llm_callbacks,
        )

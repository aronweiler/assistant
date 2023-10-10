from langchain.base_language import BaseLanguageModel
from langchain.chains.llm import LLMChain
from langchain.memory.readonly import ReadOnlySharedMemory

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_prompt
from src.ai.system_info import get_system_information


class LLMTool:
    def __init__(
        self,
        configuration,
        interaction_manager: InteractionManager,
        llm: BaseLanguageModel,
        llm_callbacks: list = [],
    ):
        self.configuration = configuration
        self.interaction_manager = interaction_manager
        self.llm = llm
        self.llm_callbacks = llm_callbacks

        memory = ReadOnlySharedMemory(memory=self.interaction_manager.conversation_token_buffer_memory)

        self.chain = LLMChain(
            llm=self.llm,
            prompt=get_prompt(
                self.configuration.model_configuration.llm_type, "CONVERSATIONAL_PROMPT"
            ),
            memory=memory,
        )

    def query_llm(self, query: str, related_context: str = None):
        """Uses an LLM to answer a query.  This is useful for when you want to just generate a response from an LLM with the given query."""
        return self.chain.run(
            system_prompt="You are a friendly AI agent who's purpose it is to answer the user's query.  Do your best to answer given the available data, and your own knowledge.  If you don't know the answer, don't make anything up, just say 'I don't know'.",
            input=query,
            user_name=self.interaction_manager.user_name,
            user_email=self.interaction_manager.user_email,
            system_information=get_system_information(
                self.interaction_manager.user_location
            ),
            context=related_context,
            loaded_documents="\n".join(
                self.interaction_manager.get_loaded_documents_for_display()
            ),
            callbacks=self.llm_callbacks,
        )

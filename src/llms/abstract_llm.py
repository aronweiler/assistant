from abc import ABC, abstractmethod
from llms.llm_result import LLMResult


class AbstractLLM(ABC):
    @abstractmethod
    def query(self, input, user_information) -> LLMResult:
        pass

    @abstractmethod
    def trim_conversation_history(self, conversation_history: list) -> list:
        pass

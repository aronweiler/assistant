from abc import ABC, abstractmethod
from llms.llm_result import LLMResult


class AbstractLLM(ABC):
    @abstractmethod
    def query(self, messages) -> LLMResult:
        pass
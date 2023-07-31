from abc import ABC, abstractmethod
from ai.ai_result import AIResult


class AbstractAI(ABC):
    @abstractmethod
    def query(self, input) -> AIResult:
        pass

    @abstractmethod
    def configure(self, json_args) -> None:
        pass

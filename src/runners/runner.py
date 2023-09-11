from abc import ABC, abstractmethod
from src.ai.abstract_ai import AbstractAI


class Runner(ABC):
    @abstractmethod
    def run(self, abstract_ai: AbstractAI):
        pass
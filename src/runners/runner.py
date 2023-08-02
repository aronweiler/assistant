from abc import ABC, abstractmethod
from ai.abstract_ai import AbstractAI


class Runner(ABC):
    @abstractmethod
    def run(self, abstract_ai: AbstractAI):
        pass
from abc import ABC, abstractmethod

from src.ai.interactions.interaction_manager import InteractionManager


# Abstract class for destinations
class DestinationBase(ABC):
    @abstractmethod
    def run(self, input: str, collection_id: str = None, llm_callbacks: list = [], agent_callbacks: list = []):
        pass

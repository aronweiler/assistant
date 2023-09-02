from abc import ABC, abstractmethod

from ai.interactions.interaction_manager import InteractionManager

# Abstract class for destinations
class DestinationBase(ABC):

    @abstractmethod
    def run(self, input:str, callbacks: list = []):
        pass

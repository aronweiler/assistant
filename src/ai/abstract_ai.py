from abc import ABC, abstractmethod

class AbstractAI(ABC):
    
    @abstractmethod
    def query(self, query: str, collection_id: int = None, callbacks: list = []):
        pass
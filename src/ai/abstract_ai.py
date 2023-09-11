from abc import ABC, abstractmethod
from typing import List

from src.db.models.users import Users
from src.utilities.instance_utility import create_instance_from_module_and_class


class AbstractAI(ABC):
    
    @abstractmethod
    def query(self, query: str, collection_id: int = None, callbacks: list = []):
        pass
from abc import ABC, abstractmethod
from typing import List
from configuration.ai_configuration import AIConfiguration
from db.models.users import Users
from utilities.instance_utility import create_instance_from_module_and_class


class AbstractAI(ABC):
    
    @abstractmethod
    def query(self, query):
        pass

    # The abstract property final_rephrase_prompt
    @property
    @abstractmethod
    def final_rephrase_prompt(self):
        pass
from abc import ABC, abstractmethod
from typing import List
from configuration.ai_configuration import AIConfiguration
from db.models.users import Users
from utilities.instance_utility import create_instance_from_module_and_class


class AbstractAI(ABC):
    def configure(self) -> None:
        self.ai_configuration: AIConfiguration        

        # Create any subordinate AIs
        # This is not really used in the GeneralAI, but I want to keep it here to remind me how to do it ;)
        if self.ai_configuration.subordinate_ais:
            self.subordinate_ais: List[AbstractAI] = []
            for sub_ai in self.ai_configuration.subordinate_ais:
                self.subordinate_ais.append(
                    create_instance_from_module_and_class(
                        sub_ai.type_configuration.module_name,
                        sub_ai.type_configuration.class_name,
                        sub_ai,
                    )
                )

    @abstractmethod
    def query(self, query, user_id: int):
        pass

    # The abstract property final_rephrase_prompt
    @property
    @abstractmethod
    def final_rephrase_prompt(self):
        pass
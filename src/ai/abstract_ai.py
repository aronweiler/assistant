from abc import ABC, abstractmethod
from typing import List
from configuration.ai_configuration import AIConfiguration
from llms.abstract_llm import AbstractLLM
from utilities.instance_utility import create_instance_from_module_and_class


class AbstractAI(ABC):
    def configure(self) -> None:
        self.ai_configuration: AIConfiguration

        # Create the primary AbstractLLM that is used by this AI
        self.llm = create_instance_from_module_and_class(
            self.ai_configuration.llm_configuration.type_configuration.module_name,
            self.ai_configuration.llm_configuration.type_configuration.class_name,
            self.ai_configuration.llm_configuration.llm_arguments_configuration,
        )

        # Create any subordinate AIs
        # This is not really used in the GeneralAI, but I want to keep it here to remind me how to do it ;)
        if self.ai_configuration.subordinate_ais:
            for sub_ai in self.ai_configuration.subordinate_ais:
                self.subordinate_ais.append(
                    AbstractAI(
                        create_instance_from_module_and_class(
                            sub_ai.type_configuration.module_name,
                            sub_ai.type_configuration.class_name,
                            sub_ai,
                        )
                    )
                )

    @abstractmethod
    def query(self, query, user_information):
        pass

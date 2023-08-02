from typing import Union, List

from configuration.ai_configuration import AIConfiguration
from ai.abstract_ai import AbstractAI
from llms.abstract_llm import AbstractLLM
from utilities.instance_utility import create_instance_from_module_and_class


class GeneralAI(AbstractAI):
    def __init__(self, ai_configuration: AIConfiguration):
        self.ai_configuration = ai_configuration

        # Initialize the AbstractLLM and dependent AIs
        self.configure()

    def query(self, query, user_information):
        self.llm: AbstractLLM
        response = self.llm.query(query, user_information)

        # General AI returns a string
        return response.result_string

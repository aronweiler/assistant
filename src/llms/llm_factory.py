from llms.abstract_llm import AbstractLLM
from configuration.llm_configuration import LLMConfiguration
from utilities.instance_utility import create_instance_from_module_and_class


class LLMFactory:
    @staticmethod
    def from_configuration(config: LLMConfiguration) -> AbstractLLM:
        # Load the specified LLM
        llm = create_instance_from_module_and_class(
            config.type_configuration.module_name,
            config.type_configuration.class_name,
            config,
            config.llm_arguments_configuration,
        )

        return llm

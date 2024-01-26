import logging
import os
import sys
import json
from langchain_core.language_models import BaseLanguageModel

from pydantic import BaseModel
from typing import Type, Dict

from src.ai.prompts.prompt_models.conversational import (
    ConversationalInput,
    ConversationalOutput,
)
from src.utilities.json_repair import JsonRepair
from src.utilities.parsing_utilities import parse_json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.ai.prompts.prompt_manager import PromptManager
from src.ai.llm_helper import get_llm
from src.ai.system_info import get_system_information
from src.utilities.configuration_utilities import get_app_configuration

from src.ai.prompts.openai_prompts.formatting_instructions import (
    FORMATTING_INSTRUCTIONS,
)


class QueryHelper:
    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager

    def query_llm(
        self,
        llm: BaseLanguageModel,
        prompt_template_name: str,
        input_class_instance,
        output_class_type: Type[BaseModel],
        **kwargs,
    ):
        # Verify that input_class_instance is an instance of a Pydantic model
        if not isinstance(input_class_instance, BaseModel):
            raise ValueError(
                "input_class_instance must be an instance of a Pydantic model"
            )

        # Convert input_class_instance to a dictionary
        input_values = input_class_instance.model_dump()

        prompt = self.prompt_manager.get_prompt_by_template_name(prompt_template_name)

        prompt = prompt.format(**input_values)

        # Generate JSON schema from the Pydantic model
        schema = output_class_type.model_json_schema()

        # Convert the schema to a JSON string
        schema_json = json.dumps(schema, indent=2)

        # Constructing a formatting prompt for the LLM using the schema information, and append it to the prompt
        prompt += "\n\n" + FORMATTING_INSTRUCTIONS.format(response_format=schema_json)

        # Invoke the language model with the converted dictionary and any additional kwargs
        result = llm.invoke(prompt, **kwargs)

        json_result = parse_json(text=result.content, llm=llm)        

        # Verify that result is a dictionary
        if not isinstance(json_result, Dict):
            raise ValueError(
                f"The output from the language model must be a dictionary, instead we got: {result.content}"
            )

        # Convert the result to the specified output_class_type
        output_values = output_class_type(**json_result)

        return output_values
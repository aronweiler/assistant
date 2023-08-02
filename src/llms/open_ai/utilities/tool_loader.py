import importlib
import logging
from typing import List
from openai_functions import FunctionWrapper
from llms.open_ai.utilities.open_ai_utilities import ToolWrapper

from configuration.tool_configuration import ToolConfiguration

from utilities.instance_utility import create_instance_from_module_and_class


def load_tool_from_config(data: ToolConfiguration):
    tool_instance = create_instance_from_module_and_class(
        data.type_configuration.module_name,
        data.type_configuration.class_name,
        data.arguments,
    )

    # get the function
    function_ref = getattr(tool_instance, data.function_name)

    wrapper = FunctionWrapper(function_ref)
    schema = wrapper.schema

    tool_wrapper = ToolWrapper(function_ref, schema)

    return tool_wrapper

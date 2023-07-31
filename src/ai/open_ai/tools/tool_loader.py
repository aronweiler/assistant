import importlib
import logging
from typing import List
from openai_functions import FunctionWrapper

from utilities.instance_tools import create_instance_from_module_and_class

from ai.open_ai.tools.tool_wrapper import OpenAIToolWrapper


class ToolLoader:
    @staticmethod
    def create_tool_instance(open_ai_tool: OpenAIToolWrapper):
        if open_ai_tool is None:
            raise Exception("open_ai_tool must be provided")

        return create_instance_from_module_and_class(
            open_ai_tool.tool_module,
            open_ai_tool.tool_class,
            open_ai_tool.tool_configuration,
        )

    # static method to load tools
    @staticmethod
    def load_tools_from_json(json_string_list) -> List[OpenAIToolWrapper]:
        tool_list = []
        for data in json_string_list:
            tool_list.append(ToolLoader.load_tool_from_json(data))
        return tool_list

    @staticmethod
    def load_tool_from_json(data) -> OpenAIToolWrapper:
        name = data.get("name", "")
        module = data.get("module", "")
        function_name = data.get("function_name", "")
        class_name = data.get("class_name", "")
        tool_configuration = data.get("tool_configuration", {})

        tool_wrapper = OpenAIToolWrapper(
            module=module,
            class_name=class_name,
            name=name,
            tool_configuration=tool_configuration,
        )

        tool = ToolLoader.create_tool_instance(tool_wrapper)
        function_ref = getattr(tool, function_name)

        wrapper = FunctionWrapper(function_ref)
        schema = wrapper.schema

        tool_wrapper.open_ai_tool = schema
        tool_wrapper.open_ai_function = function_ref

        return tool_wrapper

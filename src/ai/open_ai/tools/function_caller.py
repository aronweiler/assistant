from typing import List
import json

from ai.open_ai.tools.tool_wrapper import OpenAIToolWrapper


def call_function(function_call, tools: List[OpenAIToolWrapper]):
    function_instance = None
    for tool in tools:
        if tool.open_ai_tool["name"] == function_call["name"]:
            function_instance = tool.open_ai_function

    if function_instance:
        result = function_instance(**json.loads(function_call["arguments"]))
        return result
    else:
        raise Exception(f"Could not find function with name {function_call['name']}")

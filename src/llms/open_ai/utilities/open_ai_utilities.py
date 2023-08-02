from typing import List
#from ai.open_ai.tools.tool_wrapper import OpenAIToolWrapper


def get_openai_api_key():
    from dotenv import dotenv_values, load_dotenv

    load_dotenv()
    return dotenv_values().get("OPENAI_API_KEY")

class ToolWrapper:
    def __init__(self, function_ref, schema):
        self.open_ai_tool = schema
        self.open_ai_function = function_ref


# def get_tool_by_tool_name(tool_name, tools: List[OpenAIToolWrapper]):
#     for t in tools:
#         if t.name == tool_name:
#             return t.open_ai_tool

#     return None


# def get_tool_by_function_name(function_name, tools):
#     for t in tools:
#         if t.open_ai_tool["name"] == function_name:
#             return t.open_ai_tool

#     return None

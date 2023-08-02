from typing import List
import json


def call_function(function_call, function_instance):
    # Find the right tool to call in tools

    if function_instance:
        result = function_instance(**json.loads(function_call["arguments"]))
        return result
    else:
        raise Exception("function_instance is None")

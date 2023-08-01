import logging
import json

# For testing
# Add the root path to the python path so we can import the database
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from ai.abstract_ai import AbstractAI
from ai.ai_result import AIResult
from ai.open_ai.configuration import OpenAIConfiguration
from ai.open_ai.utilities.open_ai_utilities import (
    get_openai_api_key,
    get_tool_by_function_name,
)
from ai.open_ai.tools.function_caller import call_function
from ai.open_ai.utilities.chat_completion import OpenAIChatCompletion
from utilities.pretty_print import pretty_print_conversation, pretty_print


class ToolUsingAI(AbstractAI):
    def configure(self, json_args):
        self.configuration = OpenAIConfiguration(json_args)
        self.openai_api_key = get_openai_api_key()

        self.open_ai_completion = OpenAIChatCompletion(
            self.openai_api_key, self.configuration.model
        )

    def query(self, query):
        # query could be a "Step" object
        # If so, pull out the recommended tool
        recommended_tool = None
        if "recommended_tool" in query:
            recommended_tool = query["recommended_tool"]

        # If the query is a "Step" object, pull out the content
        if "content" in query:
            query = query["content"]

        results = []
        # The query coming in here should be something that was previously identified as a task to be completed by a tool
        results.append(
            self.get_function_call_from_initial_query(query, recommended_tool)
        )

        if "function_call" in results[0]:
            function_results = call_function(
                results[0]["function_call"], self.configuration.tools
            )
        else:
            return AIResult(
                results,
                "Failed to call a function related to this request.  TODO: Put something in here to try to automatically rephrase the query in order to call the right tool.",
            )

        # Get the results of the function call, and make sure that they answer the query / complete the task
        while function_results:
            results.append(function_results)

            results.append(
                self.is_task_complete(
                    function_results, query, json.dumps(results[0]["function_call"])
                )
            )
            function_results = None

            if "function_call" in results[-1]:
                function_results = call_function(
                    results[-1]["function_call"], self.configuration.tools
                )
            else:
                break

        result_string = "uh oh!  Something went wrong!  Look at the tool_using_ai.py file to see what happened."
        try:
            result_string = results[-1]["content"]
        except:
            pass

        return AIResult(results, result_string)

    def is_task_complete(self, function_results, initial_query, function_call):
        messages = []
        messages.append(
            {
                "role": "assistant",
                "content": "I am a digital assistant helping another digital assistant to complete their task.",
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": "The first assistant was given the instructions:",
            }
        )
        messages.append({"role": "user", "content": initial_query})
        messages.append(
            {
                "role": "assistant",
                "content": f"The first assistant then ran the following function:",
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": function_call,
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": "Which returned the following results:",
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(function_results),
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": "I will evaluate the results to determine if the task can be completed with the available data.",
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": "If the task is not complete, I will call another function I know about to complete the task.",
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": "If the task can be completed, I will respond by answering the initial query using the data available.",
            }
        )

        return self.process(messages)[-1]

    def get_function_call_from_initial_query(self, query: str, suggested_function=None):
        messages = []
        messages.append(
            {
                "role": "assistant",
                "content": "I am a powerful digital assistant capable of using a number of different tools and functions available to me to accomplish the following task.",
            }
        )
        if suggested_function:
            messages.append(
                {
                    "role": "assistant",
                    "content": "Another digital assistant has recommended the use of the following function to complete the task, please take this suggestion into account:",
                }
            )
            messages.append({"role": "user", "content": suggested_function})
        messages.append(
            {
                "role": "assistant",
                "content": "I will execute the following task using only the functions available to me:",
            }
        )
        messages.append({"role": "user", "content": query})

        result = self.process(messages, True)

        return result[-1]

    def process(self, messages: list, use_functions=True, specific_functions=None):
        # Always prepend a message with some basic info
        temp_messages = messages.copy()

        # TODO: Add the system info back in
        # temp_messages.insert(
        #     0,
        #     {
        #         "role": "system",
        #         "content": self.system_info.get(),
        #     },
        # )

        try:
            if use_functions:
                if specific_functions:
                    chat_response = self.open_ai_completion.chat_completion_request(
                        temp_messages,
                        functions=specific_functions,
                    )
                else:
                    chat_response = self.open_ai_completion.chat_completion_request(
                        temp_messages,
                        functions=[t.open_ai_tool for t in self.configuration.tools],
                    )
            else:
                chat_response = self.open_ai_completion.chat_completion_request(
                    temp_messages
                )

            if chat_response.status_code != 200:
                raise Exception(
                    f"OpenAI returned a non-200 status code: {chat_response.status_code}.  Response: {chat_response.text}"
                )

            assistant_message = chat_response.json()["choices"][0]["message"]
            messages.append(assistant_message)
            pretty_print_conversation(messages)

            return messages

        except Exception as e:
            logging.error(e)


# Testing
if __name__ == "__main__":
    test_json_args = {
        "name": "open_ai_tool_using_ai",
        "model": "gpt-3.5-turbo-0613",
        "tools": [
            {
                "name": "yelp_tool",
                "module": "ai.open_ai.tools.restaurants.yelp_tool",
                "function_name": "search_businesses",
                "class_name": "YelpTool",
            },
            {
                "name": "yelp_tool",
                "module": "ai.open_ai.tools.restaurants.yelp_tool",
                "function_name": "get_all_business_details",
                "class_name": "YelpTool",
            },
        ],
    }

    tool_ai = ToolUsingAI()
    tool_ai.configure(test_json_args)
    result = tool_ai.query(
        "Please find a highly-rated sushi restaurant near Mission Valley in San Diego."
    )

    for item in [
        None if "content" not in r else r["content"] for r in result.raw_result
    ]:
        if item is not None:
            pretty_print(item, "blue")

    # pretty_print(result.result_string, "green")

    ## MASSIVE TEST
    # test_query = 'Please research highly rated sushi restaurants in San Diego. Once you have a list of selected restaurants, please check if they offer outdoor seating options.'

    # result = tool_ai.query(test_query)

    # pretty_print(result, "green")

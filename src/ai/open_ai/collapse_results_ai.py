import logging
from ai.abstract_ai import AbstractAI
from ai.ai_result import AIResult
from ai.open_ai.utilities.open_ai_utilities import (
    get_openai_api_key,
    get_tool_by_function_name,
)
from utilities.pretty_print import pretty_print_conversation, pretty_print
from ai.open_ai.tools.function_caller import call_function
from ai.open_ai.configuration import OpenAIConfiguration
from ai.open_ai.utilities.chat_completion import OpenAIChatCompletion
from utilities.instance_tools import create_instance_from_module_and_class


class CollapseResultsAI(AbstractAI):
    def configure(self, json_args):
        self.configuration = OpenAIConfiguration(json_args)
        self.openai_api_key = get_openai_api_key()

        self.open_ai_completion = OpenAIChatCompletion(
            self.openai_api_key, self.configuration.model
        )

    def query(self, query, initial_query):
        # Query here is a list of strings
        # Collapse the strings into one string separated by newlines
        # query = "\n".join(query)

        # Feed it the AI to get it to complete the task by collapsing and summarizing the results
        result = self.complete_task(query, initial_query)

        return AIResult(result, result)

    def complete_task(self, data, initial_query):
        messages = []
        messages.append(
            {
                "role": "assistant",
                "content": "I am helping another digital assistant to complete a task.",
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": "The initial query is:",
            }
        )
        messages.append(
            {
                "role": "user",
                "content": initial_query,
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": "The other digital assistant has given me the following information, and I need to collapse and summarize the results to answer the initial query.",
            }
        )
        messages.append(
            {
                "role": "user",
                "content": "\n".join([d for d in data if d is not None]),
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": "Here is my summary of the resolution of the initial query, phrased as an answer to the initial query:",
            }
        )

        return self.process(
            messages,
        )[-1]

    def process(self, messages: list):
        try:
            chat_response = self.open_ai_completion.chat_completion_request(messages)

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

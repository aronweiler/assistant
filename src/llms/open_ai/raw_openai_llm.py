import json
import logging
from datetime import datetime
from typing import Union, List, Dict
from tools.results.summarize_result import SummarizeResult


from utilities.pretty_print import pretty_print_conversation
from utilities.token_helper import simple_get_tokens_for_message

from configuration.llm_arguments_configuration import LLMArgumentsConfiguration

from llms.abstract_llm import AbstractLLM
from llms.llm_result import LLMResult
from llms.open_ai.utilities.tool_loader import (
    load_tool_from_config,
    load_tool_from_instance,
)
from llms.open_ai.utilities.chat_completion import OpenAIChatCompletion
from llms.open_ai.utilities.open_ai_utilities import get_openai_api_key
from llms.open_ai.utilities.function_caller import call_function

from tools.general.list_tool import ListTool
from tools.general.tool_recommender import ToolRecommender

from db.database.models import User


class OpenAILLM(AbstractLLM):
    def __init__(self, llm_arguments_configuration: LLMArgumentsConfiguration):
        self.llm_arguments_configuration = llm_arguments_configuration

        logging.debug(f"Created OpenAILLM")

        # Load the OpenAI AI
        self.openai_api_key = get_openai_api_key()

        self.tools = []
        for tool in self.llm_arguments_configuration.tools:
            self.tools.append(
                {
                    "name": tool.function_name,
                    "tool_instance": load_tool_from_config(tool),
                }
            )

            logging.debug(f"Loaded tool: {tool.function_name}")

        # load up some generic tools that we will probably use
        self.generic_tools = []
        self.generic_tools.append(
            {
                "name": ListTool.create_list.__name__,
                "tool_instance": load_tool_from_instance(
                    ListTool(), ListTool.create_list.__name__
                ),
            }
        )
        self.generic_tools.append(
            {
                "name": ToolRecommender.recommend_tool.__name__,
                "tool_instance": load_tool_from_instance(
                    ToolRecommender(), ToolRecommender.recommend_tool.__name__
                ),
            },
        )
        logging.debug(f"Loaded tool: {ListTool.create_list.__name__}")

        # Create the chat completion object
        self.open_ai_completion = OpenAIChatCompletion(
            self.openai_api_key, self.llm_arguments_configuration.model
        )

    def query(self, messages, use_tools=False):
        logging.debug(f"OpenAI LLM got Query: {messages}")
        pretty_print_conversation(messages)

        if use_tools:
            chat_response = self.open_ai_completion.chat_completion_request(
                messages, [f for f in self.tools]
            )
        else:
            chat_response = self.open_ai_completion.chat_completion_request(messages)

        # TODO: What do we do if the response is a tool call?
        times_function_called = 0
        answer = []
        while (
            "function_call" in chat_response.json()["choices"][0]["message"]
            and times_function_called
            < self.llm_arguments_configuration.max_function_limit
        ):
            # We could chain function calls... but we don't want to get crazy.  Use the max_function_limit to prevent infinite loops

            function_call = chat_response.json()["choices"][0]["message"][
                "function_call"
            ]

            chat_response = self.handle_function_call(function_call)
            times_function_called += 1            

            answer += [
                {
                    "role": "system",
                    "content": f"This is attempt {times_function_called} to answer the user's query by calling a function.",
                },
                {
                    "role": "assistant",
                    "content": f"I called the {function_call['name']} function with the following arguments: {function_call['arguments']}, and the result was:",
                },
                {"role": "user", "content": "FUNCTION RESULT:" + chat_response},
                {
                    "role": "system",
                    "content": "If the content above contains an error, examine the error and think about what you could do differently.  Otherwise, use the content to answer the user's query.",
                },
                {
                    "role": "assistant",
                    "content": "Ok, I will look at the function result and see if it contains an error or the information I need to address the user's original query.",
                }
            ]

            pretty_print_conversation(answer)

            chat_response = self.open_ai_completion.chat_completion_request(
                messages + answer, [f for f in self.tools]
            )

        if times_function_called >= self.llm_arguments_configuration.max_function_limit:
            return LLMResult(
                chat_response,
                "Hit max function limit.  Something is probably wrong.",
                is_tool_result=False,
            )

        return LLMResult(
            chat_response,
            chat_response.json()["choices"][0]["message"]["content"],
            is_tool_result=False,
        )    

    def handle_function_call(self, function_call):
        try:
            function_to_call = next(
                t["tool_instance"]
                for t in self.tools
                if t["name"] == function_call["name"]
            ).open_ai_function

            function_result = call_function(function_call, function_to_call)

            # What kind of result is it?
            # TODO: Make this generic
            if type(function_result) is SummarizeResult:
                return self.summarize_results(function_result.results)

            return function_result

        except Exception as e:
            # error_result = self.handle_function_call_error(e, function_call, user_information)["content"]
            return "There was an error calling the function. " + str(e)

    def summarize_results(self, results_to_summarize):
        summaries = []
        logging.debug(f"Summarizing {len(results_to_summarize)} results")
        for result in results_to_summarize:
            prompt = [
                {
                    "role": "system",
                    "content": f"Your goal is to summarize the following text while shortening it as much as possible without losing key information.  Look at the text and think about what information is important and what information is not important.  Then, summarize the text in your own words.",
                },
                {"role": "user", "content": result},
                {
                    "role": "assistant",
                    "content": "Sure!  Here is a summary of the text (as short as I can make it without losing important information):",
                },
            ]
            
            logging.debug(f"Summarizing: {result}")
            pretty_print_conversation(prompt)

            chat_response = self.open_ai_completion.chat_completion_request(prompt)

            summaries.append(chat_response.json()["choices"][0]["message"]["content"])

        # Combine the summaries
        # If the token count is still too high, we need to summarize the summaries
        token_count = 0
        additional_summaries = []
        text = ""
        for summary in summaries:
            text += summary
            token_count += simple_get_tokens_for_message(summary)
            if token_count > 512:
                additional_summaries.append(text)
                text = ""
                token_count = 0

        if text != "":
            additional_summaries.append(text)

        # TODO: Make this configurable
        if len(additional_summaries) > 1:
            logging.debug(f"Summarizing {len(additional_summaries)} summaries")
            return self.summarize_results(additional_summaries)
        else:
            return additional_summaries[0]

    # def _process_response_with_function_call(self, assistant_message, user_information, initial_query, system_info_string):
    #     function_call = assistant_message["function_call"]
    #     logging.debug(f"Calling function: {function_call['name']}, {function_call}")
    #     function_result = self._handle_function_call(function_call, user_information)

    #     messages = [
    #         {"role": "system", "content": system_info_string},
    #         {"role": "user", "content": initial_query},
    #         {"role": "assistant", "content": f"I called '{function_call['name']}'. Here is the result:"},
    #         {"role": "assistant", "content": function_result},
    #         {"role": "assistant", "content": "Using these results, the answer to the user's query is:"},
    #     ]

    #     return self._call_underlying_llm(messages, user_information)

    # def _call_underlying_llm(
    #     self, conversation, user_information, available_functions=None, specific_functions_to_use=None, use_history=True
    # ):
    #     try:
    #         # Validate conversation messages
    #         for message in conversation:
    #             self._validate_message(message)

    #         # Get the system info
    #         system_prompt_and_info_messages = self.get_system_prompt_and_info(user_information)

    #         # If we're using conversation_history, prepend it to the messages
    #         # Then we have to trim the conversation if it goes beyond the trim_conversation_history_at_token_count
    #         # I'm including the size of the system info, too, because it's part of the conversation history
    #         # But I don't want to trim it, so I'm just doing the count
    #         if self.llm_arguments_configuration.conversation_history and use_history:
    #             token_count = self._get_token_count(self.message_history + conversation + system_prompt_and_info_messages)
    #             logging.debug(f"Conversation history token count: {token_count}")

    #             if token_count > self.llm_arguments_configuration.trim_conversation_history_at_token_count:
    #                 # Get the trimmed history
    #                 self.message_history = self.trim_conversation_history(self.message_history)

    #             conversation = self.message_history + conversation

    #         # Add the system prompt and info
    #         conversation = system_prompt_and_info_messages + conversation

    #         # Are we using functions?
    #         if available_functions:
    #             # Specific ones?
    #             if specific_functions_to_use:
    #                 logging.debug(f"Using the specific functions: {specific_functions_to_use}")
    #                 chat_response = self.open_ai_completion.chat_completion_request(
    #                     conversation,
    #                     functions=[f for f in available_functions],
    #                     function_call=specific_functions_to_use
    #                 )
    #             else:
    #                 logging.debug(f"Making all tools available to the LLM")
    #                 # Let openai decide
    #                 chat_response = self.open_ai_completion.chat_completion_request(
    #                     conversation,
    #                     functions=[f for f in available_functions],
    #                 )
    #         else:
    #             logging.debug(f"Not using functions")
    #             # Don't use functions
    #             chat_response = self.open_ai_completion.chat_completion_request(
    #                 conversation
    #             )

    #         if chat_response.status_code != 200:
    #             raise Exception(
    #                 f"OpenAI returned a non-200 status code: {chat_response.status_code}. Response: {chat_response.text}"
    #             )

    #         assistant_message = chat_response.json()["choices"][0]["message"]

    #         if "function_call" in assistant_message:
    #             return self._process_response_with_function_call(assistant_message, user_information, conversation[-1]["content"], conversation[1]["content"])

    #         if assistant_message and use_history:
    #             self.message_history.append(assistant_message)

    #         pretty_print_conversation(assistant_message)

    #         return assistant_message

    #     except Exception as e:
    #         logging.error(f"Error calling the underlying LLM: {e}")
    #         return "Something went wrong calling the underlying LLM, see the logs for more information."

    # def _get_token_count(self, messages: list) -> int:
    #     num_tokens_from_messages(messages, self.llm_arguments_configuration.model)

    # def handle_function_call_error(self, exception: Exception, function_call: dict, user_information) -> str:
    #     logging.error(f"Telling the LLM to handle the function call exception")
    #     messages = []
    #     messages.append(
    #         {
    #             "role": "assistant",
    #             "content": f"I will diagnose an error received by another digital assistant's attempt to call a function.",
    #         }
    #     )
    #     messages.append(
    #         {
    #             "role": "user",
    #             "content": "Function details: " + json.dumps(function_call),
    #         }
    #     )
    #     messages.append(
    #         {
    #             "role": "user",
    #             "content": "The exception I received is:",
    #         }
    #     )
    #     messages.append(
    #         {
    #             "role": "user",
    #             "content": str(exception),
    #         }
    #     )
    #     messages.append(
    #         {
    #             "role": "assistant",
    #             "content": "I have examined the error, the summary of which is:",
    #         }
    #     )

    #     result = self._call_underlying_llm(messages, user_information, use_history=False)

    #     return result

    # # TODO: Make this more robust- currently it just strips messages from the conversation
    # # That only works when messages are below the token count threshold
    # # When we get a single message that has a large token count, this will fail
    # # Investigate creating a generic pipeline for trimming conversation histories in all of the LLMs
    # def trim_conversation_history(self, conversation_history: List[Dict]) -> List[Dict]:
    #     logging.debug("Trimming conversation history")

    #     # Add initial assistant messages
    #     messages = [
    #         {"role": "assistant", "content": "I am shortening the conversation history to make room for the new message."},
    #         {"role": "assistant", "content": "I will shorten the following messages by summarizing, abbreviating, and eliminating unimportant information without losing any important information."},
    #         {"role": "user", "content": conversation_history},
    #         {"role": "assistant", "content": f"Here I am using 'create_list' to create a shortened conversation history by summarizing without losing any important information."},
    #     ]

    #     # Call the OpenAI API to generate a shortened conversation history
    #     chat_response = self._call_underlying_llm(messages, use_history=False)

    #     if chat_response.status_code != 200:
    #         raise Exception(f"Could not shorten conversation history. OpenAI returned a non-200 status code: {chat_response.status_code}. Response: {chat_response.text}")

    #     assistant_message = chat_response.json()["choices"][0]["message"]

    #     # Check if the assistant message contains a function call
    #     if "function_call" in assistant_message:
    #         function_results = self._handle_function_call(assistant_message["function_call"])
    #         if function_results:
    #             logging.debug("Conversation history trimmed successfully, new token count: " + str(get_token_count(function_results)))
    #             return function_results
    #     else:
    #         logging.error(f"Could not shorten conversation history. LLM did not call the tool. Assistant message: {assistant_message}")

#     logging.debug(f"Query: {input}, user: {user_information.email}")

    #     messages = []
    #     messages.append(
    #         {
    #             "role": "user",
    #             "content": input,
    #         }
    #     )

    #     result = self._call_underlying_llm(messages, user_information, self.tools)

    #     try:
    #         llm_result = LLMResult(result, result["content"])
    #     except Exception as e:
    #         logging.error(f"Error creating LLMResult: {e}")
    #         llm_result = LLMResult(result, "There was an error processing your request. Please check the logs for more information.")

    #     return llm_result

    # def get_system_prompt_and_info(self, user_information: User):
    #     messages = []
    #     for prompt in self.llm_arguments_configuration.system_prompts:
    #         messages.append(
    #             {
    #                 "role": "system",
    #                 "content": prompt
    #             }
    #         )
    #     system_info_string = f"System Info: Current Date/Time: {datetime.now()}, User Email: {user_information.email}, User Location: {user_information.location}, User Name: {user_information.name}, User Age: {user_information.age}"
    #     messages.append(
    #         {
    #             "role": "system",
    #             "content": system_info_string,
    #         }
    #     )

    #     return messages

    # def _validate_message(self, message):
    #     if not isinstance(message, dict) or "role" not in message or "content" not in message:
    #         raise ValueError("Each message should be a dictionary with 'role' and 'content' keys.")
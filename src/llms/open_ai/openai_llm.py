import openai
import logging
from datetime import datetime

from utilities.pretty_print import pretty_print_conversation
from utilities.token_helper import get_token_count

from configuration.llm_arguments_configuration import LLMArgumentsConfiguration

from llms.abstract_llm import AbstractLLM
from llms.llm_result import LLMResult
from llms.open_ai.utilities.tool_loader import load_tool_from_config
from llms.open_ai.utilities.chat_completion import OpenAIChatCompletion
from llms.open_ai.utilities.open_ai_utilities import get_openai_api_key
from llms.open_ai.utilities.function_caller import call_function

from tools.general.list_tool import ListTool

from db.database.models import User


class OpenAILLM(AbstractLLM):
    def __init__(self, llm_arguments_configuration: LLMArgumentsConfiguration):
        self.llm_arguments_configuration = llm_arguments_configuration

        logging.debug(f"Created OpenAILLM {self.llm_arguments_configuration}")

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
                "tool_instance": ListTool(),
            }
        )
        logging.debug(f"Loaded tool: {ListTool.create_list.__name__}")       

        # Set up the underlying LLM and any tools
        self.open_ai_completion = OpenAIChatCompletion(
            self.openai_api_key, self.llm_arguments_configuration.model
        )

        # Initialize the message history
        self.message_history = []

    def query(self, input, user_information: User):
        logging.debug(f"Query: {input}, user: {user_information.email}")
        
        messages = []        
        messages.append(
            {
                "role": "user",
                "content": input,
            }
        )

        result = self._call_underlying_llm(messages, user_information, self.tools)

        return LLMResult(result, result["content"])
    
    def get_system_prompt_and_info(self, user_information: User):
        messages = []
        messages.append(
            {
                "role": "system",
                "content": self.llm_arguments_configuration.system_prompt,
            }
        )
        system_info_string = f"System Info: Current Date/Time: {datetime.now()}, User Email: {user_information.email}, User Location: {user_information.location}, User Name: {user_information.name}, User Age: {user_information.age}"
        messages.append(
            {
                "role": "system",
                "content": system_info_string,
            }
        )

        return messages

    def _call_underlying_llm(
        self, messages: list, user_information: User, available_functions=None, specific_functions_to_use=None
    ):
        try:
            # Get the system info
            system_prompt_and_info_messages = self.get_system_prompt_and_info(user_information)            
            # If we're using conversation_history, prepend it to the messages
            # Then we have to trim the conversation if it goes beyond the trim_conversation_history_at_token_count
            # I'm including the size of the system info, too, because it's part of the conversation history
            # But I don't want to trim it, so I'm just doing the count
            if self.llm_arguments_configuration.conversation_history:
                token_count = self._get_token_count(self.message_history + messages + system_prompt_and_info_messages)
                logging.debug(f"Conversation history token count: {token_count}")

                if (
                    token_count
                    > self.llm_arguments_configuration.trim_conversation_history_at_token_count
                ):
                    # Get the trimmed history
                    self.message_history = self.trim_conversation_history(
                        self.message_history
                    )

                messages = self.message_history + messages

            # Add the system prompt and info
            messages = system_prompt_and_info_messages + messages

            # Are we using functions?
            if available_functions:
                # Specific ones?
                if specific_functions_to_use:
                    logging.debug(f"Using the specific functions: {specific_functions_to_use}")
                    chat_response = self.open_ai_completion.chat_completion_request(
                        messages,
                        functions=[f for f in available_functions],
                        function_call=specific_functions_to_use
                    )
                else:
                    logging.debug(f"Making all tools available to the LLM")
                    # Let openai decide
                    chat_response = self.open_ai_completion.chat_completion_request(
                        messages,
                        functions=[f for f in available_functions],
                    )
            else:
                logging.debug(f"Not using functions")
                # Don't use functions
                chat_response = self.open_ai_completion.chat_completion_request(
                    messages
                )

            if chat_response.status_code != 200:
                raise Exception(
                    f"OpenAI returned a non-200 status code: {chat_response.status_code}.  Response: {chat_response.text}"
                )

            assistant_message = chat_response.json()["choices"][0]["message"]

            if "function_call" in assistant_message:
                function_to_call = [
                    t["tool_instance"]
                    for t in self.tools
                    if t["name"] == assistant_message["function_call"]["name"]
                ][0].open_ai_function

                logging.debug(f"Calling function: {assistant_message['function_call']['name']}")
                function_result = call_function(
                    assistant_message["function_call"],
                    function_to_call,
                )
                
                # Run the response through the LLM again to get a summary / response
                messages.append(
                    {
                        "role": "user",
                        "content": f"I called '{assistant_message['function_call']['name']}'.  Here is the result:",
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": function_result,
                    }
                )
                messages.append(
                    {
                        "role": "assistant",
                        "content": "Using these results, the answer to the user's query is:",
                    }
                )
                assistant_message = self._call_underlying_llm(messages, user_information, self.tools)

            self.message_history.append(assistant_message)

            pretty_print_conversation(assistant_message)

            return assistant_message

        except Exception as e:
            logging.error(e)

    def _get_token_count(self, messages: list) -> int:
        token_count = 0
        for message in messages:
            token_count += get_token_count(message["content"])

        return token_count

    def trim_conversation_history(self, conversation_history: list) -> list:
        logging.debug("Trimming conversation history")

        messages = []
        messages.append(
            {
                "role": "assistant",
                "content": "I am shortening the conversation history to make room for the new message.",
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": "I will shorten the following messages as much as possible by summarizing, abbreviating, and eliminating unimportant information without losing any important information.",
            }
        )
        messages.append(
            {
                "role": "user",
                "content": conversation_history,
            }
        )
        messages.append(
            {
                "role": "assistant",
                "content": f"Here I am using '{ListTool.create_list.__name__}' to create a shortened conversation history by summarizing without losing any important information.",
            }
        )

        chat_response = self.open_ai_completion.chat_completion_request(
            messages, functions=[self.generic_tools], function_call="create_list"
        )

        if chat_response.status_code != 200:
            raise Exception(
                f"Could not shorten conversation history. OpenAI returned a non-200 status code: {chat_response.status_code}.  Response: {chat_response.text}"
            )

        assistant_message = chat_response.json()["choices"][0]["message"]

        # assistant_message should be a function call to shorten the conversation history
        if "function_call" in assistant_message:
            logging.debug(f"Calling function: {assistant_message['function_call']}")
            function_results = call_function(
                assistant_message["function_call"], self.configuration.tools
            )

            if function_results:
                # Should be a list of messages
                logging.debug("Conversation history trimmed successfully, new token count: " + str(get_token_count(function_results)))
                return function_results
        else:
            raise Exception(
                f"Could not shorten conversation history. Failed to call the function to shorten the conversation history.  Assistant message: {assistant_message}"
            )

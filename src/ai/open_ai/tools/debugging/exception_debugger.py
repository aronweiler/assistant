import openai

from ai.open_ai.utilities.chat_completion import OpenAIChatCompletion
from utilities.pretty_print import pretty_print_conversation


class ExceptionDebugger:
    def __init__(self, api_key, model):
        self.api_key = api_key
        openai.api_key = api_key
        self.model = model

    def debug_exception(self, exception, model=None, print_summary=True):
        if model is None:
            model = self.model

        chat_completion = OpenAIChatCompletion(self.api_key, self.model)

        # Convert the exception into a string for GPT-3.5-turbo input
        exception_text = f"Please diagnose this exception for me:\n{type(exception).__name__}: {str(exception)}"

        messages = []
        messages.append(
            {
                "role": "system",
                "content": "You are a helpful programmer who is debugging a program.",
            }
        )
        messages.append(
            {
                "role": "user",
                "content": "Give me your best guess as to why this is happening.",
            }
        )
        messages.append(
            {
                "role": "user",
                "content": "Include examples of how I might troubleshoot this.",
            }
        )
        messages.append({"role": "user", "content": exception_text})

        # Extract the summary from the response
        chat_response = chat_completion.chat_completion_request(messages)

        if chat_response.status_code != 200:
            pretty_print_conversation(chat_response.json(), "red")
        else:
            assistant_message = chat_response.json()["choices"][0]["message"]
            messages.append(assistant_message)
            pretty_print_conversation(assistant_message, "blue")

            return messages

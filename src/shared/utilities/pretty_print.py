from termcolor import colored


def pretty_print(message, color="green"):
    print(colored(message, color))


def pretty_print_conversation(messages, color="green"):
    role_to_color = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "function": "magenta",
        "error": "red",
        "custom": color,
    }

    if isinstance(messages, str):
        print(colored(messages, color))
    elif isinstance(messages, dict):
        single_message = [{"role": "custom", "content": messages}]
        pretty_print_conversation(single_message, color)
    elif isinstance(messages, list):
        for message in messages:
            role = message.get("role", "other")
            content = message.get("content", "")
            if role in role_to_color:
                color_code = role_to_color[role]
                if role == "assistant" and message.get("function_call"):
                    content = message["function_call"]
                print(colored(f"{role}: {content}\n", color_code))
            else:
                print(colored(f"other: {content}\n", color))
    else:
        print(
            colored(
                "Invalid input format. Expected a string, a dictionary, or a list of messages.",
                "red",
            )
        )


# Testing when we call this file directly
if __name__ == "__main__":
    # Example usage:
    messages_list = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "function", "name": "some_function", "content": "Function executed."},
        {"role": "error", "content": "Error occurred."},
    ]
    pretty_print_conversation(messages_list)

    single_message = "This is a single message."
    pretty_print_conversation(single_message, color="yellow")

from termcolor import colored

def pretty_print(message, color = "green"):
    print(colored(message, color))

# print arrays and single strings in a pretty way
def pretty_print_conversation(messages, color = "green"):
    role_to_color = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "function": "magenta",
        "error": "red",
        "custom": color
    }

    if isinstance(messages, str):
        print(colored(messages, color))
        return
    elif isinstance(messages, list) and all(isinstance(msg, str) for msg in messages):
        for message in messages:
            if message["role"] == "system":
                print(colored(f"system: {message['content']}\n", role_to_color[message["role"]]))
            elif message["role"] == "user":
                print(colored(f"user: {message['content']}\n", role_to_color[message["role"]]))
            elif message["role"] == "assistant" and message.get("function_call"):
                print(colored(f"assistant: {message['function_call']}\n", role_to_color[message["role"]]))
            elif message["role"] == "assistant" and not message.get("function_call"):
                print(colored(f"assistant: {message['content']}\n", role_to_color[message["role"]]))
            elif message["role"] == "function":
                print(colored(f"function ({message['name']}): {message['content']}\n", role_to_color[message["role"]]))
            elif message["role"] == "error":
                print(colored(f"error: {message['content']}\n", role_to_color[message["role"]]))
            else:
                print(colored(f"other: {message['content']}\n", color))
from collections import defaultdict
import inspect


# This dictionary will hold all tool classes
registered_tools = defaultdict(list)


def tool_class(cls):
    """Decorator to register tool classes."""
    print(f"Registering tool {cls.__name__}.")

    registered_tools[cls.__module__]["class"] = cls

    return cls


# Decorator to register a tool function along with its metadata
def register_tool(
    display_name,
    description,
    additional_instructions=None,
    help_text=None,
    requires_documents=False,
    requires_repository=False,
    document_classes=[],
):
    if help_text is None:
        help_text = description

    def decorator(func):
        func._tool_metadata = {
            "description": description,
            "additional_instructions": additional_instructions,
            "document_classes": document_classes,
            "display_name": display_name,
            "help_text": help_text,
            "requires_documents": requires_documents,
            "requires_repository": requires_repository,
        }

        if func.__module__ not in registered_tools:
            registered_tools[func.__module__] = {"functions": {}}

        registered_tools[func.__module__]["functions"][func.__name__] = {
            "function": func
        }

        return func

    return decorator


def get_tool_functions(cls):
    tool_functions = {}
    for name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
        if hasattr(func, "tool_function"):
            print(
                f"Function {name} in class {cls.__name__} has the @tool_function attribute."
            )
            tool_functions[name] = func

    return tool_functions

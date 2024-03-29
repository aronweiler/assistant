from collections import defaultdict
import inspect
import logging

# This dictionary will hold all tool classes with their associated functions and metadata
registered_tools = defaultdict(list)


# Decorator to register tool classes
def tool_class(cls):
    """Decorator to register tool classes."""
    # Print a message indicating which tool class is being registered
    logging.info(f"Registering tool {cls.__name__}.")

    # Add the class to the registered_tools dictionary under its module name
    registered_tools[cls.__module__]["class"] = cls

    # Return the class itself after registration
    return cls


# Decorator to register a tool function along with its metadata
def register_tool(
    display_name:str,    
    description:str,
    additional_instructions:str=None,
    help_text:str=None,
    requires_documents:bool=False,
    requires_repository:bool=False,
    document_classes:list[str]=[],
    category:str = None,
    enabled_by_default:bool = True,
    include_in_conversation:bool = False,
    return_direct:bool = False,
    requires_llm:bool = False,
):
    """Decorator to register a tool function along with its metadata.
    
    Args:
        display_name (str): The display name of the tool.
        description (str): The description of the tool.
        additional_instructions (str, optional): Additional instructions for the tool. Defaults to None.
        help_text (str, optional): The help text for the tool. Defaults to None.
        requires_documents (bool, optional): Whether the tool requires documents. Defaults to False.
        requires_repository (bool, optional): Whether the tool requires a repository. Defaults to False.
        document_classes (list[str], optional): The list of document classes the tool can handle. Defaults to [].
        category (str, optional): The category of the tool. Defaults to None.
        enabled_by_default (bool, optional): Whether the tool is enabled by default. Defaults to True.
        include_in_conversation (bool, optional): Whether the tool is included in the conversation. Defaults to False.
        return_direct (bool, optional): Whether the tool returns directly. Defaults to False.
        requires_llm (bool, optional): Whether the tool requires an LLM. Defaults to False."""
    # If no help_text is provided, use the description as help_text
    if help_text is None:
        help_text = description

    # Define the actual decorator function
    def decorator(func):
        # Attach metadata to the function using a special attribute
        func._tool_metadata = {
            "description": description,
            "additional_instructions": additional_instructions,
            "document_classes": document_classes,
            "display_name": display_name,
            "help_text": help_text,
            "requires_documents": requires_documents,
            "requires_repository": requires_repository,
            "category": category,
            "enabled_by_default": enabled_by_default,
            "include_in_conversation": include_in_conversation,
            "return_direct": return_direct,
            "requires_llm": requires_llm,
        }

        # If the module is not already in the registered_tools, initialize it
        if func.__module__ not in registered_tools:
            registered_tools[func.__module__] = {"functions": {}}

        # Register the function in the registered_tools dictionary
        registered_tools[func.__module__]["functions"][func.__name__] = {
            "function": func
        }

        # Return the function after adding the metadata
        return func

    # Return the decorator function
    return decorator


# Function to retrieve tool functions from a class
def get_tool_functions(cls):
    # Initialize an empty dictionary to hold tool functions
    tool_functions = {}
    # Iterate over all members of the class that are functions
    for name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
        # Check if the function has the 'tool_function' attribute
        if hasattr(func, "tool_function"):
            # Print a message indicating the function has the 'tool_function' attribute
            logging.info(
                f"Function {name} in class {cls.__name__} has the @tool_function attribute."
            )
            # Add the function to the tool_functions dictionary
            tool_functions[name] = func

    # Return the dictionary of tool functions
    return tool_functions

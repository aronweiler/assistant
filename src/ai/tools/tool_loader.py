import logging
import pkgutil
import importlib
import inspect
import sys
import os


# Append the path to the tools directory to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.ai.tools.tool_registry import registered_tools
from src.ai.agents.general.generic_tools_agent import GenericTool
from src.utilities.configuration_utilities import get_app_configuration


# Function to load all modules in the 'tools' directory
def load_tool_modules():
    package = "src.tools"
    package_path = package.replace(".", "/")

    def load_recursive(package_name, path):
        for loader, module_name, is_pkg in pkgutil.walk_packages([path]):
            full_module_name = f"{package_name}.{module_name}"
            if is_pkg:
                next_path = path + "/" + module_name
                load_recursive(full_module_name, next_path)
            else:
                try:
                    importlib.import_module(full_module_name)
                except Exception as e:
                    logging.error(f"Could not load module {full_module_name}, {e}")

    load_recursive(package, package_path)


def get_available_tools(configuration, conversation_manager):
    # Load all tool modules to ensure they are registered
    load_tool_modules()

    generic_tools = {}
    # Initialize all registered tools with dependencies
    for module_name, tool_info in registered_tools.items():
        # Inject dependencies based on the function signature
        dependencies = {
            "configuration": configuration,
            "conversation_manager": conversation_manager,
        }
        # You can add logic here to determine which dependencies are needed
        # for each tool and inject them accordingly

        if "class" not in tool_info:
            for function_name, function_info in tool_info["functions"].items():
                generic_tool = create_generic_tool(
                    configuration, function_name, function_info["function"]
                )

                generic_tools[function_name] = generic_tool

        else:
            # Get the constructor parameters for the class
            constructor_params = inspect.signature(
                tool_info["class"].__init__
            ).parameters

            # Filter out only the necessary dependencies that match the constructor parameters
            filtered_dependencies = {
                k: v for k, v in dependencies.items() if k in constructor_params
            }

            # Initialize the tool with the filtered dependencies
            tool_instance = tool_info["class"](**filtered_dependencies)

            for function_name, function_info in tool_info["functions"].items():
                func = getattr(tool_instance, function_name)
                generic_tool = create_generic_tool(configuration, function_name, func)
                generic_tools[function_name] = generic_tool

    return generic_tools


def create_generic_tool(configuration, function_name, func):
    if hasattr(func, "_tool_metadata"):
        tool_metadata = func._tool_metadata

    if function_name in configuration["tool_configurations"]:
        return_direct = configuration["tool_configurations"][function_name].get(
            "return_direct", False
        )
    else:
        return_direct = False

    generic_tool = GenericTool(
        description=tool_metadata.get("description", function_name),
        additional_instructions=tool_metadata.get("additional_instructions", None),
        function=func,
        name=function_name,
        return_direct=return_direct,
        document_classes=tool_metadata.get("document_classes", []),
    )

    return generic_tool


# Testing
if __name__ == "__main__":
    configuration = get_app_configuration()
    conversation_manager = None
    get_available_tools(
        configuration=configuration, conversation_manager=conversation_manager
    )

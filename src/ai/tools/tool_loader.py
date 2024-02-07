import logging
import pkgutil
import importlib
import inspect
import sys
import os
from src.ai.conversations.conversation_manager import ConversationManager
from src.db.models.user_settings import UserSettings
from src.ai.tools.tool_registry import registered_tools
from src.ai.agents.general.generic_tool import GenericTool
from src.utilities.configuration_utilities import get_app_configuration

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Constants
PACKAGE = "src.tools"
PACKAGE_PATH = PACKAGE.replace(".", "/")


def load_module(full_module_name):
    """Load a single module by its full module name."""
    try:
        importlib.import_module(full_module_name)
    except Exception as e:
        logging.error(f"Could not load module {full_module_name}, {e}")


def load_recursive(package_name, path):
    """Recursively load modules from a given package and path."""
    for loader, module_name, is_pkg in pkgutil.walk_packages([path]):
        if loader.path.replace("\\", "/").endswith(path):
            full_module_name = f"{package_name}.{module_name}"
            if is_pkg:
                next_path = path + "/" + module_name
                load_recursive(full_module_name, next_path)
            else:
                load_module(full_module_name)


def load_tool_modules():
    """Load all modules in the 'tools' directory."""
    load_recursive(PACKAGE, PACKAGE_PATH)


def get_available_tools(configuration, conversation_manager):
    load_tool_modules()
    generic_tools = []
    for module_name, tool_info in registered_tools.items():
        dependencies = {
            "configuration": configuration,
            "conversation_manager": conversation_manager,
        }
        if "class" not in tool_info:
            for function_name, function_info in tool_info["functions"].items():
                generic_tool = create_generic_tool(
                    function_name,
                    function_info["function"],
                    conversation_manager,
                )
                generic_tools.append(generic_tool)
        else:
            constructor_params = inspect.signature(
                tool_info["class"].__init__
            ).parameters
            filtered_dependencies = {
                k: v for k, v in dependencies.items() if k in constructor_params
            }
            tool_instance = tool_info["class"](**filtered_dependencies)
            for function_name, function_info in tool_info["functions"].items():
                func = getattr(tool_instance, function_name)
                generic_tool = create_generic_tool(
                    function_name, func, conversation_manager
                )
                generic_tools.append(generic_tool)
    return generic_tools


def get_tool_setting(
    function_name,
    setting_name,
    conversation_manager: ConversationManager,
    default_value=None,
):
    return conversation_manager.user_settings_helper.get_user_setting(
        user_id=conversation_manager.user_id,
        setting_name=function_name + "_" + setting_name,
        default_value=default_value,
    ).setting_value


def create_generic_tool(function_name, func, conversation_manager: ConversationManager):
    tool_metadata = getattr(func, "_tool_metadata", {})
    return_direct = get_tool_setting(
        function_name=function_name,
        setting_name="return_direct",
        conversation_manager=conversation_manager,
        default_value=tool_metadata.get("return_direct", False),
    )
    generic_tool = GenericTool(
        description=tool_metadata.get("description", function_name),
        additional_instructions=tool_metadata.get("additional_instructions", None),
        function=func,
        name=function_name,
        return_direct=return_direct,
        document_classes=tool_metadata.get("document_classes", []),
        display_name=tool_metadata.get("display_name", function_name),
        requires_documents=tool_metadata.get("requires_documents", False),
        help_text=tool_metadata.get("help_text", None),
        requires_repository=tool_metadata.get("requires_repository", False),
    )
    return generic_tool


if __name__ == "__main__":
    configuration = get_app_configuration()
    conversation_manager = None
    get_available_tools(
        configuration=configuration, conversation_manager=conversation_manager
    )

import os
from src.configuration.assistant_configuration import ApplicationConfigurationLoader


def get_tool_configuration(configuration: dict, func_name: str) -> dict:
    """
    Retrieve the tool-specific configuration.

    Parameters:
        configuration (dict): The main configuration dictionary containing all tool configurations.
        func_name (str): The name of the function for which to retrieve the configuration.

    Returns:
        dict: The configuration dictionary for the specified function or the default configuration if not found.
    """
    if func_name in configuration["tool_configurations"]:
        return configuration["tool_configurations"][func_name]

    return configuration["tool_configurations"]["default"]


def get_app_config_path() -> str:
    """
    Get the file system path to the application configuration file.

    Returns:
        str: The path to the application configuration file, either from the environment variable or the default path.
    """
    app_config_path = os.environ.get(
        "APP_CONFIG_PATH",
        "configurations/app_configs/config.json",
    )

    return app_config_path


def get_app_configuration() -> dict:
    """
    Load the application configuration from the configuration file.

    Returns:
        dict: The application configuration loaded from the file.
    """
    app_config_path = get_app_config_path()

    return ApplicationConfigurationLoader.from_file(app_config_path)

import os
from src.configuration.assistant_configuration import ApplicationConfigurationLoader


def get_tool_configuration(configuration: dict, func_name: str) -> dict:
    """
    Retrieves the tool configuration for a given function name from the provided configuration dictionary.

    Parameters:
        configuration (dict): The configuration dictionary containing tool configurations.
        func_name (str): The name of the function for which to retrieve the tool configuration.

    Returns:
        dict: The tool configuration dictionary for the specified function, or the default configuration if not found.
    """
    if func_name in configuration["tool_configurations"]:
        return configuration["tool_configurations"][func_name]

    return configuration["tool_configurations"]["default"]


def get_app_config_path() -> str:
    """
    Determines the file path to the application configuration file.

    Returns:
        str: The file path to the application configuration file, either from the APP_CONFIG_PATH environment variable or a default path.
    """
    app_config_path = os.environ.get(
        "APP_CONFIG_PATH",
        "configurations/app_configs/config.json",
    )

    return app_config_path


def get_app_configuration() -> dict:
    """
    Loads the application configuration from the file specified by the get_app_config_path function.

    Returns:
        dict: The application configuration loaded from the file.
    """
    app_config_path = get_app_config_path()

    return ApplicationConfigurationLoader.from_file(app_config_path)

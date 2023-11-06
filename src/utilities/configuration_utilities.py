import os
from src.configuration.assistant_configuration import ApplicationConfigurationLoader


def get_tool_configuration(configuration: dict, func_name: str) -> dict:
    if func_name in configuration["tool_configurations"]:
        return configuration["tool_configurations"][func_name]

    return configuration["tool_configurations"]["default"]


def get_app_config_path():
    app_config_path = os.environ.get(
        "APP_CONFIG_PATH",
        "configurations/app_configs/config.json",
    )

    return app_config_path


def get_app_configuration():
    """Loads the configuration from the path"""
    app_config_path = get_app_config_path()

    return ApplicationConfigurationLoader.from_file(app_config_path)

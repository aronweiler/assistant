import os
from src.shared.configuration.assistant_configuration import ApplicationConfigurationLoader
from src.shared.configuration.voice_configuration import VoiceConfiguration


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

def get_voice_config_path():
    voice_config_path = os.environ.get(
        "VOICE_CONFIG_PATH",
        "configurations/app_configs/voice.json",
    )

    return voice_config_path


def get_app_configuration():
    """Loads the configuration from the path"""
    app_config_path = get_app_config_path()

    return ApplicationConfigurationLoader.from_file(app_config_path)

def get_voice_configuration():
    """Loads the configuration from the path"""
    app_config_path = get_voice_config_path()

    return VoiceConfiguration.from_file(app_config_path)

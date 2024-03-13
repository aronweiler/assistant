import os
import discord
import uuid

# include the root directory in the path so we can import the configuration
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.shared.configuration.assistant_configuration import (
    ApplicationConfigurationLoader,
)


def get_discord_config_path():
    app_config_path = os.environ.get(
        "APP_CONFIG_PATH",
        "configurations/app_configs/discord.json",
    )

    return app_config_path


def load_configuration():
    """Loads the configuration from the path"""
    discord_config_path = get_discord_config_path()

    return ApplicationConfigurationLoader.from_file(discord_config_path)


if __name__ == "__main__":
    # Load the discord configuration

    # Iterate through each of the bots in the configuration and start them

    pass

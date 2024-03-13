import os
import discord
import uuid

# include the root directory in the path so we can import the configuration
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.shared.utilities.configuration_utilities import (
    get_app_configuration,
    get_app_config_path,
)

from src.shared.ai.utilities.llm_helper import get_llm
from src.shared.ai.prompts.prompt_manager import PromptManager

from src.shared.configuration.assistant_configuration import (
    ApplicationConfigurationLoader,
)
from src.shared.ai.rag_ai import RetrievalAugmentedGenerationAI

from src.discord.conversational_bot import ConversationalBot
from src.discord.rag_bot import RagBot


def load_configuration():
    """Loads the configuration from the path"""
    app_config_path = get_app_config_path()

    return ApplicationConfigurationLoader.from_file(app_config_path)


def load_rag_ai(
    configuration,
    intents,
    prompt_manager,
    discord_bot_email,
    discord_bot_target_channel_name,
    collection_id,
    conversation_id,
):
    """Loads the AI from the configuration"""

    return RagBot(
        intents=intents,
        configuration=configuration,
        target_channel_name=discord_bot_target_channel_name,
        target_collection_id=collection_id,
        conversation_id=conversation_id,
        prompt_manager=prompt_manager,
        user_email=discord_bot_email,
    )


def get_the_llm(configuration):
    configuration.model_configuration.temperature = 1.0

    llm = get_llm(
        configuration.model_configuration,
        tags=["jarvis-discord-bot"],
        streaming=False,
        model_kwargs={
            "frequency_penalty": 0.9,
            "presence_penalty": 0.6,
        },
    )

    return llm


def load_conversational_ai(
    configuration,
    intents,
    prompt_manager,
    discord_bot_target_channel_name,
    discord_bot_conversation_template,
):
    llm = get_the_llm(configuration)
    return ConversationalBot(
        intents=intents,
        configuration=configuration,
        llm=llm,
        target_channel_name=discord_bot_target_channel_name,
        prompt_manager=prompt_manager,
        conversation_template=discord_bot_conversation_template,
    )


if __name__ == "__main__":
    # Get the token from the environment
    discord_token = os.environ.get("DISCORD_BOT_TOKEN")
    discord_conversation_id = os.environ.get("DISCORD_INTERACTION_ID", uuid.uuid4())
    discord_collection_id = os.environ.get("DISCORD_COLLECTION_ID", None)
    discord_bot_email = os.environ.get("DISCORD_BOT_EMAIL")
    discord_bot_target_channel_name = os.environ.get(
        "DISCORD_BOT_TARGET_CHANNEL_NAME", "General"
    )
    discord_bot_conversation_template = os.environ.get(
        "DISCORD_BOT_CONVERSATION_TEMPLATE", "DISCORD_TEMPLATE"
    )
    discord_bot_type = os.environ.get("DISCORD_BOT_TYPE", "conversational")

    configuration = load_configuration()
    prompt_manager = PromptManager(
        llm_type=configuration["jarvis_ai"]["model_configuration"]["llm_type"]
    )

    intents = discord.Intents.default()
    intents.message_content = True

    if discord_bot_type.lower() == "rag":
        client = load_rag_ai(
            intents=intents,
            configuration=configuration,
            conversation_id=discord_conversation_id,
            discord_bot_email=discord_bot_email,
            discord_bot_target_channel_name=discord_bot_target_channel_name,
            collection_id=discord_collection_id,
            prompt_manager=prompt_manager,
        )
    elif discord_bot_type.lower() == "conversational":
        client = load_conversational_ai(
            configuration=configuration,
            intents=intents,
            prompt_manager=prompt_manager,
            discord_bot_target_channel_name=discord_bot_target_channel_name,
            discord_bot_conversation_template=discord_bot_conversation_template,
        )

    client.run(discord_token)

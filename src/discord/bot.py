import os
import discord

# include the root directory in the path so we can import the configuration
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.ai.llm_helper import get_llm

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfigurationLoader,
)
from src.ai.rag_ai import RetrievalAugmentedGenerationAI

from src.discord.conversational_bot import ConversationalBot

def load_configuration():
    """Loads the configuration from the path"""
    rag_config_path = os.environ.get(
        "RAG_CONFIG_PATH",
        "configurations/rag_configs/openai_rag.json",
    )

    return RetrievalAugmentedGenerationConfigurationLoader.from_file(rag_config_path)


def load_rag_ai(configuration, discord_interaction_id, discord_bot_email):
    """Loads the AI from the configuration"""
    return RetrievalAugmentedGenerationAI(
        configuration=configuration,
        interaction_id=discord_interaction_id,
        user_email=discord_bot_email,
        streaming=False,
    )


def get_the_llm(configuration):
    configuration.model_configuration.temperature = 1.0

    llm = get_llm(
        configuration.model_configuration,
        tags=["jarvis-discord-bot"],
        streaming=False,
        model_kwargs={
            "frequency_penalty": 1.5,
            "presence_penalty": 1.5,
        },
    )

    return llm


def set_tool_environment_variables():
    # Tools I want to enable for this discord bot
    # TODO: Move tools out of env so that we can have multiple bots with different tools
    os.environ["search_loaded_documents"] = "True"
    os.environ["analyze_with_llm"] = "True"
    os.environ["summarize_search_topic"] = "True"

    # Tools I want to disable for this discord bot
    os.environ["summarize_entire_document"] = "False"
    os.environ["list_documents"] = "False"
    os.environ["get_code_details"] = "False"
    os.environ["get_code_structure"] = "False"
    os.environ["get_pretty_dependency_graph"] = "False"
    os.environ["create_stubs"] = "False"
    os.environ["get_all_code_in_file"] = "False"
    os.environ["conduct_code_review_from_file_id"] = "False"
    os.environ["conduct_code_review_from_url"] = "False"
    os.environ["create_code_review_issue_tool"] = "False"
    os.environ["query_spreadsheet"] = "False"
    os.environ["get_weather"] = "False"
    os.environ["get_time"] = "False"
    os.environ["get_news_for_topic"] = "False"
    os.environ["get_top_news_headlines"] = "False"


if __name__ == "__main__":
    # Get the token from the environment
    discord_token = os.environ.get("DISCORD_BOT_TOKEN")
    discord_interaction_id = os.environ.get("DISCORD_INTERACTION_ID")
    discord_bot_email = os.environ.get("DISCORD_BOT_EMAIL")
    discord_bot_target_channel_name = os.environ.get("DISCORD_BOT_TARGET_CHANNEL_NAME", "General")
    discord_bot_conversation_template = os.environ.get("DISCORD_BOT_CONVERSATION_TEMPLATE", "DISCORD_TEMPLATE")

    set_tool_environment_variables()

    configuration = load_configuration()
    ai = load_rag_ai(configuration, discord_interaction_id, discord_bot_email)
    llm = get_the_llm(configuration)

    # Run it!
    intents = discord.Intents.default()
    intents.message_content = True
    client = ConversationalBot(intents=intents, configuration=configuration, llm=llm, target_channel_name=discord_bot_target_channel_name, conversation_template=discord_bot_conversation_template)
    client.run(discord_token)

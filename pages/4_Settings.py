import logging
import streamlit as st
import os

from src.configuration.assistant_configuration import (
    ApplicationConfigurationLoader,
)

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.tools.tool_manager import ToolManager


def get_app_configuration():
    """Loads the configuration from the path"""
    app_config_path = os.environ.get(
        "APP_CONFIG_PATH",
        "configurations/app_configs/config.json",
    )

    return ApplicationConfigurationLoader.from_file(app_config_path)


def settings_page():
    st.title("Settings")
    settings_tab, tools_tab = st.tabs(["General Settings", "Tools"])

    with settings_tab:
        general_settings()

    with tools_tab:
        tools_settings()


def generate_model_settings(name, config):
    with st.expander(
        label=f"{config['display_name']} Model Settings",
        expanded=False
    ):
        st.selectbox(
            label="Model",
            options=["openai","llama"],
            key=f"{name}-model"
        )

        st.slider(
            label="Temperature",
            key=f"{name}-temperature",
            min_value=0.,
            max_value=1.,
            step=0.01,
            value=0.
        )

        st.number_input(
            label="Max Retries",
            key=f"{name}-max-retries",
            min_value=0,
            max_value=5,
            value=3,
            step=1
        )

        st.write("Max supported tokens is 16384")

        st.number_input(
            label="Max Conversation History Tokens",
            key=f"{name}-max-conversation-history-tokens",
            min_value=0,
            max_value=4096,
            value=4096,
            step=1
        )

        st.number_input(
            label="Max Completion Tokens",
            key=f"{name}-max-completion-tokens",
            min_value=0,
            max_value=6096,
            value=6096,
            step=1
        )


def tools_settings():
    configuration = get_app_configuration()
    tool_manager = ToolManager(
        configuration=configuration
    )

    tools = tool_manager.get_all_tools()

    # Create a toggle to enable/disable each tool
    for tool_name, tool_config in tools.items():
        st.toggle(
            tool_config["display_name"],
            help=tool_config["help_text"],
            value=tool_manager.is_tool_enabled(tool_name),
            key=tool_name,
            on_change=tool_manager.toggle_tool,
            kwargs={"tool_name": tool_name},
        )

        if 'model_configuration' in configuration['tool_configurations'][tool_name]:
            generate_model_settings(
                name=tool_name,
                config=tool_config
            )


def general_settings():
    source_control_options = ["GitLab", "GitHub"]
    source_control_provider = st.selectbox(
        "Source Control Provider",
        source_control_options,
        index=source_control_options.index(
            os.getenv("SOURCE_CONTROL_PROVIDER", "GitHub")
        ),
    )

    # Source Code URL
    source_code_url = st.text_input("Source Code URL", os.getenv("SOURCE_CONTROL_URL"))

    # Source Code Personal Access Token (PAT)
    pat = st.text_input(
        "Source Code Personal Access Token (PAT)",
        type="password",
        value=os.getenv("SOURCE_CONTROL_PAT"),
    )

    # Debug Logging
    logging_options = ["DEBUG", "INFO", "WARN"]
    debug_logging = st.selectbox(
        "Logging Level",
        logging_options,
        index=logging_options.index(os.getenv("LOGGING_LEVEL", "INFO")),
    )

    # LLM Model selection box
    # llm_model_options = ["gpt-3.5-turbo-16k", "gpt-3.5-turbo", "gpt-4"]
    # llm_model = st.selectbox("LLM Model", llm_model_options, index=llm_model_options.index(os.getenv("LLM_MODEL", "gpt-3.5-turbo")))

    # Save button
    if st.button("Save Settings"):
        # Set the environment variables
        os.environ["SOURCE_CONTROL_PROVIDER"] = source_control_provider

        if source_code_url:
            os.environ["SOURCE_CONTROL_URL"] = source_code_url

        if pat:
            os.environ["SOURCE_CONTROL_PAT"] = pat

        os.environ["LOGGING_LEVEL"] = str(debug_logging)
        logging.basicConfig(level=debug_logging)

        # os.environ["LLM_MODEL"] = llm_model

        # Process and save the settings here (e.g., to a file or database)
        # For demonstration purposes, we'll just print them
        print(
            f"SOURCE_CONTROL_PROVIDER: {os.getenv('SOURCE_CONTROL_PROVIDER', 'NOT SET')}"
        )
        print(f"SOURCE_CONTROL_URL: {os.getenv('SOURCE_CONTROL_URL', 'NOT SET')}")
        print(f"SOURCE_CONTROL_PAT: {os.getenv('SOURCE_CONTROL_PAT', 'NOT SET')}")
        print(f"LOGGING_LEVEL: {os.getenv('LOGGING_LEVEL', 'NOT SET')}")
        # print(f"LLM_MODEL: {os.getenv('LLM_MODEL', 'NOT SET')}")


# Run the settings page
if __name__ == "__main__":
    settings_page()

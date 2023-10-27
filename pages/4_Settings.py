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


def get_available_models():
    available_models_path = os.environ.get(
        "AVAILABLE_MODELS",
        "configurations/available_models.json",
    )

    return ApplicationConfigurationLoader.from_file(available_models_path)


def settings_page():
    st.title("Settings")
    settings_tab, tools_tab = st.tabs(["General Settings", "Tools"])

    with settings_tab:
        general_settings()

    with tools_tab:
        tools_settings()


def generate_model_settings(
    tool_name, tool_details, tool_configuration, available_models
):
    available_model_names = [
        {available_models[m]["model_configuration"]["model"]: m}
        for m in available_models.keys()
    ]

    # index = next((i for i, item in enumerate(available_models.keys()) if available_models[item]["model_configuration"]["model"] == "gpt-3.5-turbo-16k"), None)

    with st.expander(
        label=f"{tool_details['display_name']} Model Settings", expanded=False
    ):
        col1, col2, col3 = st.columns(3)
        col1.selectbox(
            label="Model",
            options=available_model_names,
            format_func=lambda x: list(x.values())[0],
            index=next(
                (
                    i
                    for i, item in enumerate(available_models.keys())
                    if available_models[item]["model_configuration"]["model"]
                    == tool_configuration["model_configuration"]["model"]
                ),
                None,
            ),
            key=f"{tool_name}-model",
        )

        col2.slider(
            label="Temperature",
            key=f"{tool_name}-temperature",
            min_value=0.0,
            max_value=1.0,
            step=0.10,
            value=float(tool_configuration["model_configuration"]["temperature"]),
        )

        col3.slider(
            label="Max Retries",
            key=f"{tool_name}-max-retries",
            min_value=0,
            max_value=5,
            value=tool_configuration["model_configuration"]["max_retries"],
            step=1,
        )

        max_supported_tokens = int(
            available_models[list(st.session_state[f"{tool_name}-model"].values())[0]][
                "model_configuration"
            ]["max_model_supported_tokens"]
        )

        def update_sliders(max_supported_tokens, history_tokens, completion_tokens):
            available_tokens = max_supported_tokens - history_tokens
            if available_tokens < 0:
                history_tokens = max_supported_tokens
                completion_tokens = 0
            elif available_tokens < completion_tokens:
                history_tokens = max_supported_tokens - completion_tokens

            return history_tokens, completion_tokens

        history_tokens, completion_tokens = st.slider(
            "Token Allocation",
            0,
            max_supported_tokens,
            (
                int(
                    tool_configuration["model_configuration"][
                        "max_conversation_history_tokens"
                    ]
                ),
                int(tool_configuration["model_configuration"]["max_completion_tokens"]),
            ),
            key=f"{tool_name}-token-allocation"
        )

        history_tokens, completion_tokens = update_sliders(
            max_supported_tokens, history_tokens, completion_tokens
        )

        prompt_tokens = max_supported_tokens - (history_tokens + completion_tokens)
        desired_prompt_tokens = int(0.25 * max_supported_tokens)
        
        st.markdown(f"You have an available pool of **{max_supported_tokens}** tokens.  You are currently using **{history_tokens}** for conversation history and **{completion_tokens}** for completion.")
        st.markdown(f"These settings leave {':red[**only ' if prompt_tokens < desired_prompt_tokens else ':green[**'}{prompt_tokens}**] available for prompt tokens.")
        
        if(prompt_tokens < desired_prompt_tokens):
            st.markdown(f":red[*It is recommended that you leave at least {desired_prompt_tokens} tokens for prompt generation.*]")


def tools_settings():
    configuration = get_app_configuration()
    tool_manager = ToolManager(configuration=configuration)

    tools = tool_manager.get_all_tools()

    available_models = get_available_models()

    # Create a toggle to enable/disable each tool
    for tool_name, tool_details in tools.items():
        tool_configuration = configuration["tool_configurations"][tool_name]

        st.toggle(
            tool_details["display_name"],
            help=tool_details["help_text"],
            value=tool_manager.is_tool_enabled(tool_name),
            key=tool_name,
            on_change=tool_manager.toggle_tool,
            kwargs={"tool_name": tool_name},
        )

        if "model_configuration" in configuration["tool_configurations"][tool_name]:
            generate_model_settings(
                tool_name=tool_name,
                tool_details=tool_details,
                tool_configuration=tool_configuration,
                available_models=available_models,
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

import logging
import threading
import streamlit as st
import os
from google_auth_oauthlib.flow import InstalledAppFlow
import json

from src.configuration.assistant_configuration import (
    ApplicationConfigurationLoader,
)

from src.utilities.configuration_utilities import (
    get_app_config_path,
)

from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.tools.tool_manager import ToolManager

import src.ui.streamlit_shared as ui_shared

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def settings_page():
    st.set_page_config(
        page_title="Jarvis - Settings",
        page_icon="⚙️",
        layout="centered",
        initial_sidebar_state="expanded",
    )

    st.title("Settings")

    settings_tab, jarvis_ai, tools_tab, google_auth = st.tabs(
        ["General Settings", "Jarvis AI", "Tools", "Google Auth"]
    )

    with settings_tab:
        general_settings()

    with jarvis_ai:
        jarvis_ai_settings()

    with tools_tab:
        tools_settings()

    with google_auth:
        google_auth_settings()


def google_auth_settings():
    if st.button("Register Client"):
        register_client()


def register_client():
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secrets.json", SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob"
    )

    authorization_url, _ = flow.authorization_url(prompt="consent")

    st.write("Please visit the following URL to authorize your application:")
    st.write(authorization_url)

    authorization_code = st.text_input("Enter the authorization code:")

    if authorization_code:
        flow.fetch_token(authorization_response=authorization_code)

        credentials = flow.credentials
        save_credentials(credentials)

        st.success("Client registration successful!")


def save_credentials(credentials):
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    with open(
        os.environ.get("GOOGLE_CREDENTIALS_FILE_LOCATION", "google_credentials.json"),
        "w",
    ) as f:
        json.dump(token_data, f)


def jarvis_ai_settings():
    st.markdown(
        "This section allows you to configure the main Jarvis AI.  These settings will apply to the top-level model used for all interactions."
    )
    st.markdown(
        "Note: To some extent, the settings here will filter down- for instance, since the chat memory of the underlying tool models inherits from the top-level model, the chat memory will be limited to the number of tokens set here."
    )
    st.divider()

    # Flag to indicate if we need to save the settings
    needs_saving = False

    jarvis_config = ui_shared.get_app_configuration()["jarvis_ai"]

    st.markdown("### General")

    needs_saving = show_thoughts(jarvis_config, needs_saving)

    st.divider()

    st.markdown("### Jarvis AI Model Settings")

    generate_model_settings(
        tool_name="jarvis",
        tool_configuration=jarvis_config,
        available_models=ui_shared.get_available_models(),
    )

    model_configuration, needs_saving = model_needs_saving(
        tool_name="jarvis",
        existing_tool_configuration=jarvis_config,
        needs_saving=needs_saving,
    )

    st.markdown("### File Ingestion Settings")

    generate_model_settings(
        tool_name="jarvis-file-ingestion",
        tool_configuration=jarvis_config["file_ingestion_configuration"],
        available_models=ui_shared.get_available_models(),
    )

    file_ingestion_model_configuration, needs_saving = model_needs_saving(
        tool_name="jarvis-file-ingestion",
        existing_tool_configuration=jarvis_config["file_ingestion_configuration"],
        needs_saving=needs_saving,
    )

    if needs_saving:
        st.toast(f"Saving Jarvis AI settings...")
        save_jarvis_settings_to_file(
            show_llm_thoughts=st.session_state["show_llm_thoughts"],
            model_configuration=model_configuration,
            file_ingestion_model_configuration=file_ingestion_model_configuration,
        )


def show_thoughts(jarvis_config, needs_saving):
    st.toggle(
        label="Show LLM Thoughts",
        value=jarvis_config.get("show_llm_thoughts", False),
        key="show_llm_thoughts",
    )
    st.markdown(
        "When enabled, Jarvis will show the LLM's thoughts as it is generating a response."
    )

    if st.session_state["show_llm_thoughts"] != jarvis_config.get(
        "show_llm_thoughts", False
    ):
        needs_saving = True

    return needs_saving


def generate_model_settings(tool_name, tool_configuration, available_models):
    available_model_names = [
        {available_models[m]["model_configuration"]["model"]: m}
        for m in available_models.keys()
    ]

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

    max_model_completion_tokens = int(
        available_models[list(st.session_state[f"{tool_name}-model"].values())[0]][
            "model_configuration"
        ].get("max_model_completion_tokens", max_supported_tokens)
    )

    st_sucks_col1, st_sucks_col2 = st.columns([4, 6])

    st_sucks_col1.toggle(
        "Use Conversation History",
        value=tool_configuration["model_configuration"]["uses_conversation_history"],
        key=f"{tool_name}-uses-conversation-history",
    )
    st_sucks_col2.markdown("Turn this on to use conversation history for the model.")
    st_sucks_col2.markdown(
        "*Note: This will not give memory to the tools that do not use it.*"
    )

    st_sucks_col1.number_input(
        "Model Seed Value",
        value=tool_configuration["model_configuration"]["model_kwargs"].get("seed", 500)
        if "model_kwargs" in tool_configuration["model_configuration"]
        else 500,
        key=f"{tool_name}-seed",
    )
    st_sucks_col2.markdown("Set this to a value to seed the model.  ")
    st_sucks_col2.markdown(
        "Same seed values in the same requests will produce more deterministic results."
    )

    def update_sliders(
        max_supported_tokens,
        max_model_completion_tokens,
        chat_history_tokens,
        completion_tokens,
    ):
        # Some models have a maximum completion token limit
        if completion_tokens > max_model_completion_tokens:
            completion_tokens = max_model_completion_tokens

        available_tokens = max_supported_tokens - chat_history_tokens
        if available_tokens < 0:
            chat_history_tokens = max_supported_tokens
            completion_tokens = 0
        elif available_tokens < completion_tokens:
            chat_history_tokens = max_supported_tokens - completion_tokens

        return chat_history_tokens, completion_tokens

    configured_completion_tokens = int(
        tool_configuration["model_configuration"]["max_completion_tokens"]
    )

    configured_max_conversation_history_tokens = int(
        tool_configuration["model_configuration"]["max_conversation_history_tokens"]
    )

    history_tokens = st.slider(
        label="Conversation History Tokens",
        min_value=0,
        max_value=max_supported_tokens,
        value=configured_max_conversation_history_tokens,
        key=f"{tool_name}-conversation-history-tokens",
        disabled=st.session_state[f"{tool_name}-uses-conversation-history"] is False,
    )

    completion_tokens = st.slider(
        label="Completion Tokens",
        min_value=0,
        max_value=max_model_completion_tokens,
        value=min(configured_completion_tokens, max_model_completion_tokens),
        key=f"{tool_name}-completion-tokens",
    )

    history_tokens, completion_tokens = update_sliders(
        max_supported_tokens=max_supported_tokens,
        max_model_completion_tokens=max_model_completion_tokens,
        chat_history_tokens=history_tokens,
        completion_tokens=completion_tokens,
    )

    prompt_tokens = max_supported_tokens - (history_tokens + completion_tokens)
    desired_prompt_tokens = int(0.25 * max_supported_tokens)

    st.markdown(
        f"You have an available pool of **{max_supported_tokens}** tokens.  You are currently using **{history_tokens}** for conversation history and **{completion_tokens}** for completion."
    )
    st.markdown(
        f"These settings leave {':red[**only ' if prompt_tokens < desired_prompt_tokens else ':green[**'}{prompt_tokens}**] available for prompt tokens."
    )

    if prompt_tokens < desired_prompt_tokens:
        st.markdown(
            f":red[*It is recommended that you leave at least {desired_prompt_tokens} tokens for prompt generation.*]"
        )


def show_additional_settings(configuration, tool_name, tool_details):
    # If there are additional settings, get the settings and show the widgets
    if "additional_settings" in configuration["tool_configurations"][tool_name]:
        with st.expander(
            label=f"🦿 {tool_details['display_name']} Additional Settings",
            expanded=False,
        ):
            additional_settings = configuration["tool_configurations"][tool_name][
                "additional_settings"
            ]

            for additional_setting_name in additional_settings:
                additional_setting = additional_settings[additional_setting_name]
                session_state_key = f"{tool_name}-{additional_setting_name}"
                if additional_setting["type"] == "int":
                    int_setting(
                        tool_name,
                        additional_setting_name,
                        additional_setting,
                        session_state_key,
                    )
                elif additional_setting["type"] == "bool":
                    bool_setting(
                        tool_name,
                        additional_setting_name,
                        additional_setting,
                        session_state_key,
                    )

                st.markdown(additional_setting["description"])


def bool_setting(
    tool_name, additional_setting_name, additional_setting, session_state_key
):
    st.toggle(
        label=additional_setting["label"],
        value=additional_setting["value"],
        key=session_state_key,
        on_change=save_additional_setting,
        kwargs={
            "tool_name": tool_name,
            "setting_name": additional_setting_name,
            "session_state_key": session_state_key,
        },
    )


def int_setting(
    tool_name, additional_setting_name, additional_setting, session_state_key
):
    st.number_input(
        label=additional_setting["label"],
        value=additional_setting["value"],
        key=session_state_key,
        min_value=additional_setting["min"],
        max_value=additional_setting["max"],
        step=additional_setting["step"],
        on_change=save_additional_setting,
        kwargs={
            "tool_name": tool_name,
            "setting_name": additional_setting_name,
            "session_state_key": session_state_key,
        },
    )


def show_model_settings(configuration, tool_name, tool_details):
    if "model_configuration" in configuration["tool_configurations"][tool_name]:
        available_models = ui_shared.get_available_models()
        tool_configuration = configuration["tool_configurations"][tool_name]

        with st.expander(
            label=f"⚙️ {tool_details['display_name']} Model Settings",
            expanded=False,
        ):
            generate_model_settings(
                tool_name=tool_name,
                tool_configuration=tool_configuration,
                available_models=available_models,
            )


def tools_settings():
    configuration = ui_shared.get_app_configuration()
    tool_manager = ToolManager(configuration=configuration)

    tools = tool_manager.get_all_tools()

    # Create a toggle to enable/disable each tool
    for tool_name, tool_details in tools.items():
        st.markdown(f"#### {tool_details['display_name']}")
        st.markdown(tool_details["help_text"])
        col1, col2, col3 = st.columns([3, 5, 5])
        col1.toggle(
            "Enabled",
            value=tool_manager.is_tool_enabled(tool_name),
            key=tool_name,
            on_change=tool_manager.toggle_tool,
            kwargs={"tool_name": tool_name},
        )
        col2.toggle(
            "Return results directly to UI",
            value=tool_manager.should_return_direct(tool_name),
            help="Occasionally it is useful to have the results returned directly to the UI instead of having the AI re-interpret them, such as when you want to see the raw output of a tool.\n\n*Note: If `return direct` is set, the AI will not perform any tasks after this one completes.*",
            key=f"{tool_name}-return-direct",
            on_change=tool_manager.toggle_tool,
            kwargs={"tool_name": tool_name},
        )

        show_model_settings(configuration, tool_name, tool_details)
        show_additional_settings(configuration, tool_name, tool_details)

        st.divider()

    save_tool_settings(tools, configuration)


def save_tool_settings(tools, configuration):
    # Iterate through all of the tools and save their settings
    for tool_name, tool_details in tools.items():
        existing_tool_configuration = configuration["tool_configurations"][tool_name]

        # Only save if the settings are different
        needs_saving = False

        enabled = st.session_state[tool_name]
        if enabled != existing_tool_configuration["enabled"]:
            needs_saving = True

        return_direct = st.session_state[f"{tool_name}-return-direct"]
        if return_direct != existing_tool_configuration["return_direct"]:
            needs_saving = True

        model_configuration, needs_saving = model_needs_saving(
            tool_name, existing_tool_configuration, needs_saving
        )

        if needs_saving:
            st.toast(f"Saving {tool_name} settings...")
            save_tool_settings_to_file(
                tool_name=tool_name,
                enabled=enabled,
                return_direct=return_direct,
                model_configuration=model_configuration,
            )


def model_needs_saving(tool_name, existing_tool_configuration, needs_saving):
    model_configuration = None
    if "model_configuration" in existing_tool_configuration:
        # Get the model configuration from the UI

        model = list(st.session_state[f"{tool_name}-model"])[0]
        model_friendly_name = st.session_state[f"{tool_name}-model"][
            list(st.session_state[f"{tool_name}-model"])[0]
        ]
        max_model_supported_tokens = int(
            ui_shared.get_available_models()[model_friendly_name][
                "model_configuration"
            ]["max_model_supported_tokens"]
        )
        llm_type = ui_shared.get_available_models()[model_friendly_name][
            "model_configuration"
        ]["llm_type"]
        if model != existing_tool_configuration["model_configuration"]["model"]:
            needs_saving = True

        uses_conversation_history = st.session_state[
            f"{tool_name}-uses-conversation-history"
        ]
        if (
            uses_conversation_history
            != existing_tool_configuration["model_configuration"][
                "uses_conversation_history"
            ]
        ):
            needs_saving = True

        max_conversation_history_tokens = st.session_state[
            f"{tool_name}-conversation-history-tokens"
        ]
        max_completion_tokens = st.session_state[f"{tool_name}-completion-tokens"]

        if (
            max_conversation_history_tokens
            != existing_tool_configuration["model_configuration"][
                "max_conversation_history_tokens"
            ]
        ):
            needs_saving = True
        if (
            max_completion_tokens
            != existing_tool_configuration["model_configuration"][
                "max_completion_tokens"
            ]
        ):
            needs_saving = True
        max_retries = st.session_state[f"{tool_name}-max-retries"]
        if (
            max_retries
            != existing_tool_configuration["model_configuration"]["max_retries"]
        ):
            needs_saving = True

        temperature = st.session_state[f"{tool_name}-temperature"]
        if (
            temperature
            != existing_tool_configuration["model_configuration"]["temperature"]
        ):
            needs_saving = True

        seed = st.session_state[f"{tool_name}-seed"]
        if (
            "model_kwargs" not in existing_tool_configuration["model_configuration"]
            or seed
            != existing_tool_configuration["model_configuration"]["model_kwargs"][
                "seed"
            ]
        ):
            needs_saving = True

        model_configuration = {
            "llm_type": llm_type,
            "model": model,
            "temperature": temperature,
            "max_retries": max_retries,
            "max_model_supported_tokens": max_model_supported_tokens,
            "uses_conversation_history": uses_conversation_history,
            "max_conversation_history_tokens": max_conversation_history_tokens,
            "max_completion_tokens": max_completion_tokens,
            "model_kwargs": {"seed": seed},
        }

    return model_configuration, needs_saving


def save_jarvis_settings_to_file(
    show_llm_thoughts, model_configuration, file_ingestion_model_configuration
):
    configuration = ui_shared.get_app_configuration()

    configuration["jarvis_ai"]["show_llm_thoughts"] = show_llm_thoughts

    if model_configuration:
        configuration["jarvis_ai"]["model_configuration"] = model_configuration

    if file_ingestion_model_configuration:
        configuration["jarvis_ai"]["file_ingestion_configuration"][
            "model_configuration"
        ] = file_ingestion_model_configuration

    app_config_path = get_app_config_path()

    ApplicationConfigurationLoader.save_to_file(configuration, app_config_path)

    if "rag_ai" in st.session_state:
        del st.session_state["rag_ai"]

    st.session_state["app_config"] = configuration


def save_tool_settings_to_file(tool_name, enabled, return_direct, model_configuration):
    configuration = ui_shared.get_app_configuration()
    configuration["tool_configurations"][tool_name]["enabled"] = enabled
    configuration["tool_configurations"][tool_name]["return_direct"] = return_direct
    if model_configuration:
        configuration["tool_configurations"][tool_name][
            "model_configuration"
        ] = model_configuration

    app_config_path = get_app_config_path()

    ApplicationConfigurationLoader.save_to_file(configuration, app_config_path)

    if "rag_ai" in st.session_state:
        del st.session_state["rag_ai"]

    st.session_state["app_config"] = configuration


def save_additional_setting(tool_name, setting_name, session_state_key):
    configuration = ui_shared.get_app_configuration()
    settings = configuration["tool_configurations"][tool_name]["additional_settings"]

    settings[setting_name]["value"] = st.session_state[session_state_key]

    app_config_path = get_app_config_path()

    ApplicationConfigurationLoader.save_to_file(configuration, app_config_path)

    if "rag_ai" in st.session_state:
        del st.session_state["rag_ai"]

    st.session_state["app_config"] = configuration


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

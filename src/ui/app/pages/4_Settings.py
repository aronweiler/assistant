import logging
import sys
import streamlit as st
import os
#from google_auth_oauthlib.flow import InstalledAppFlow
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from utilities import ensure_authenticated

from src.shared.ai.tools.tool_loader import get_available_tools

from src.shared.configuration.model_configuration import ModelConfiguration
from src.shared.database.models.code import Code
from src.shared.database.models.domain.source_control_provider_model import (
    SourceControlProviderModel,
)
from src.shared.database.models.user_settings import UserSettings


from src.shared.ai.conversations.conversation_manager import ConversationManager
from src.shared.ai.tools.tool_manager import ToolManager

import streamlit_shared as ui_shared
from utilities import ensure_authenticated

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def settings_page(user_email):
    # st.set_page_config(
    #     page_title="Jarvis - Settings",
    #     page_icon="⚙️",
    #     layout="centered",
    #     initial_sidebar_state="expanded",
    # )

    st.title("Settings")

    # Initialize or get current tab index from session state
    if "current_tab" not in st.session_state:
        st.session_state["current_tab"] = 0

    # Define your tabs and store them in a list
    tabs = ["General Settings", "Jarvis Web AI", "Jarvis Voice AI", "Source Control", "Tools", "Jama"]

    # Set callback function for on_change event of tabs
    def on_tab_change():
        st.session_state["current_tab"] = tabs.index(st.session_state["selected_tab"])

    # Add a selectbox for changing tabs that uses session state
    selected_tab = st.selectbox(
        "Setting selection",
        options=tabs,
        index=st.session_state["current_tab"],
        key="selected_tab",
        on_change=on_tab_change,
    )

    st.caption(
        "Use the setting selection to choose which settings you would like to view or change."
    )
    st.divider()

    conversation_manager = ConversationManager(
        conversation_id=None, user_email=user_email, prompt_manager=None
    )

    # Now use an if-else block or match-case to render content based on selected tab
    if selected_tab == "General Settings":
        general_settings()
    elif selected_tab == "Jarvis Web AI":    
        jarvis_ai_settings(conversation_manager=conversation_manager)
    elif selected_tab == "Jarvis Voice AI":
        jarvis_voice_ai_settings(conversation_manager=conversation_manager)
    elif selected_tab == "Source Control":
        source_control_provider_form()
    elif selected_tab == "Tools":
        tools_settings(conversation_manager=conversation_manager)
    elif selected_tab == "Jama":
        jama_settings(conversation_manager=conversation_manager)
    # elif selected_tab == "Google Auth":
    #     google_auth_settings()


def jama_settings(conversation_manager: ConversationManager):
    st.subheader("Jama Configuration")

    if "rag_ai" not in st.session_state:
        st.error(
            "The AI is not currently running.  Please start the AI by navigating to the `Jarvis` tab, and then return here to configure Jama settings."
        )
        return

    user_settings_helper = UserSettings()
    user_id = conversation_manager.user_id

    jama_api_url = st.text_input(
        "Jama API URL",
        value=user_settings_helper.get_user_setting(
            user_id, "jama_api_url"
        ).setting_value,
    )
    jama_client_id = st.text_input(
        "Jama Client ID",
        value=user_settings_helper.get_user_setting(
            user_id, "jama_client_id"
        ).setting_value,
    )
    jama_client_secret = st.text_input(
        "Jama Client Secret",
        value=user_settings_helper.get_user_setting(
            user_id, "jama_client_secret"
        ).setting_value,
    )

    if st.button("Save Jama Settings"):
        save_jama_settings_to_file(
            jama_api_url,
            jama_client_id,
            jama_client_secret,
            conversation_manager=conversation_manager,
        )


# def google_auth_settings():
#     if st.button("Register Client"):
#         register_client()


# def register_client():
#     flow = InstalledAppFlow.from_client_secrets_file(
#         "client_secrets.json", SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob"
#     )

#     authorization_url, _ = flow.authorization_url(prompt="consent")

#     st.write("Please visit the following URL to authorize your application:")
#     st.write(authorization_url)

#     authorization_code = st.text_input("Enter the authorization code:")

#     if authorization_code:
#         flow.fetch_token(authorization_response=authorization_code)

#         credentials = flow.credentials
#         save_credentials(credentials)

#         st.success("Client registration successful!")


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


def jarvis_ai_settings(conversation_manager: ConversationManager):
    st.markdown(
        "This section allows you to configure the main Jarvis AI.  These settings will apply to the top-level model used for all interactions."
    )
    st.markdown(
        "Note: To some extent, the settings here will filter down- for instance, since the chat memory of the underlying tool models inherits from the top-level model, the chat memory will be limited to the number of tokens set here."
    )
    st.divider()

    # Flag to indicate if we need to save the settings
    needs_saving = False

    # Special case
    default_jarvis_model = ModelConfiguration.default()        
    # Ensure that the main model uses conversation history if its never been used before
    default_jarvis_model.uses_conversation_history = True
    default_jarvis_model.max_conversation_history_tokens = 16384    

    jarvis_setting = json.loads(
        UserSettings()
        .get_user_setting(
            conversation_manager.user_id,
            "jarvis_ai_model_configuration",
            default_value=default_jarvis_model.model_dump_json(),
        )
        .setting_value
    )

    jarvis_ai_model_configuration = ModelConfiguration(**jarvis_setting)

    ingestion_setting = json.loads(
        UserSettings()
        .get_user_setting(
            conversation_manager.user_id,
            "file_ingestion_model_configuration",
            default_value=ModelConfiguration.default().model_dump_json(),
        )
        .setting_value
    )

    file_ingestion_model_configuration = ModelConfiguration(**ingestion_setting)

    st.markdown("### General")

    show_thoughts(conversation_manager=conversation_manager)

    st.divider()

    st.markdown("### Jarvis AI Model Settings")

    generate_model_settings(
        tool_name="jarvis_ai",
        model_configuration=jarvis_ai_model_configuration,
        available_models=ui_shared.get_available_models(),
        conversation_manager=conversation_manager,
    )

    needs_saving = model_configuration_needs_saving(
        tool_name="jarvis_ai",
        existing_model_configuration=jarvis_ai_model_configuration,
        needs_saving=needs_saving,
    )

    st.markdown("### File Ingestion Settings")

    generate_model_settings(
        tool_name="jarvis_file_ingestion",
        model_configuration=file_ingestion_model_configuration,
        available_models=ui_shared.get_available_models(),
        conversation_manager=conversation_manager,
    )

    needs_saving = model_configuration_needs_saving(
        tool_name="jarvis_file_ingestion",
        existing_model_configuration=file_ingestion_model_configuration,
        needs_saving=needs_saving,
    )

    if needs_saving:
        st.toast(f"Saving Jarvis AI settings...")
        save_jarvis_settings(
            jarvis_ai_model_configuration=jarvis_ai_model_configuration,
            file_ingestion_model_configuration=file_ingestion_model_configuration,
            conversation_manager=conversation_manager,
        )

def jarvis_voice_ai_settings(conversation_manager: ConversationManager):
    st.markdown(
        "This section allows you to configure the Jarvis Voice AI.  These settings will apply to the top-level model used for all interactions."
    )
    st.markdown(
        "Note: To some extent, the settings here will filter down- for instance, since the chat memory of the underlying tool models inherits from the top-level model, the chat memory will be limited to the number of tokens set here."
    )
    st.divider()

    # Flag to indicate if we need to save the settings
    needs_saving = False

    # Special case
    default_jarvis_voice_model = ModelConfiguration.default()        
    # Ensure that the main model uses conversation history if its never been used before
    default_jarvis_voice_model.uses_conversation_history = True
    default_jarvis_voice_model.max_conversation_history_tokens = 16384    

    jarvis_setting = json.loads(
        UserSettings()
        .get_user_setting(
            conversation_manager.user_id,
            "jarvis_voice_ai_model_configuration",
            default_value=default_jarvis_voice_model.model_dump_json(),
        )
        .setting_value
    )

    jarvis_voice_ai_model_configuration = ModelConfiguration(**jarvis_setting)    

    st.markdown("### General")

    show_thoughts(conversation_manager=conversation_manager)

    st.divider()

    st.markdown("### Jarvis AI Model Settings")

    generate_model_settings(
        tool_name="jarvis_voice_ai",
        model_configuration=jarvis_voice_ai_model_configuration,
        available_models=ui_shared.get_available_models(),
        conversation_manager=conversation_manager,
    )

    needs_saving = model_configuration_needs_saving(
        tool_name="jarvis_voice_ai",
        existing_model_configuration=jarvis_voice_ai_model_configuration,
        needs_saving=needs_saving,
    )

    if needs_saving:
        st.toast(f"Saving Jarvis Voice AI settings...")
        save_jarvis_voice_settings(
            jarvis_ai_model_configuration=jarvis_voice_ai_model_configuration,
            conversation_manager=conversation_manager,
        )

def show_thoughts(conversation_manager: ConversationManager):

    # Get the show thoughts setting
    existing_show_thoughts = bool(
        UserSettings()
        .get_user_setting(
            conversation_manager.user_id, "show_llm_thoughts", default_value=True
        )
        .setting_value
    )

    st.toggle(
        label="Show LLM Thoughts",
        value=existing_show_thoughts,
        key="show_llm_thoughts",
        on_change=save_additional_setting,
        kwargs={
            "setting_name": "show_llm_thoughts",
            "session_state_key": "show_llm_thoughts",
            "conversation_manager": conversation_manager,
        },
    )
    st.markdown(
        "When enabled, Jarvis will show the LLM's thoughts as it is generating a response."
    )


def save_show_thoughts(conversation_manager: ConversationManager):
    # Get the value of the slider from the session
    UserSettings().add_update_user_setting(
        user_id=conversation_manager.user_id,
        setting_name="show_llm_thoughts",
        setting_value=st.session_state["show_llm_thoughts"],
        available_for_llm=True,
    )


def generate_model_settings(
    tool_name,
    model_configuration: ModelConfiguration,
    available_models,
    conversation_manager: ConversationManager,
):
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
                == model_configuration.model
            ),
            None,
        ),
        key=f"{tool_name}_model",
        on_change=save_model_setting,
        kwargs={
            "model_owner_name": tool_name,
            "conversation_manager": conversation_manager,
        },
    )

    col2.slider(
        label="Temperature",
        key=f"{tool_name}_temperature",
        min_value=0.0,
        max_value=1.0,
        step=0.10,
        value=float(model_configuration.temperature),
        on_change=save_model_setting,
        kwargs={
            "model_owner_name": tool_name,
            "conversation_manager": conversation_manager,
        },
    )

    col3.slider(
        label="Max Retries",
        key=f"{tool_name}_max_retries",
        min_value=0,
        max_value=5,
        value=model_configuration.max_retries,
        step=1,
        on_change=save_model_setting,
        kwargs={
            "model_owner_name": tool_name,
            "conversation_manager": conversation_manager,
        },
    )

    max_supported_tokens = int(
        available_models[list(st.session_state[f"{tool_name}_model"].values())[0]][
            "model_configuration"
        ]["max_model_supported_tokens"]
    )

    # Model settings get saved separately- no on_change event
    max_model_completion_tokens = int(
        available_models[list(st.session_state[f"{tool_name}_model"].values())[0]][
            "model_configuration"
        ].get("max_model_completion_tokens", max_supported_tokens)
    )

    st_sucks_col1, st_sucks_col2 = st.columns([4, 6])

    # Model settings get saved separately- no on_change event
    st_sucks_col1.toggle(
        "Use Conversation History",
        value=model_configuration.uses_conversation_history,
        key=f"{tool_name}_uses_conversation_history",
        on_change=save_model_setting,
        kwargs={
            "model_owner_name": tool_name,
            "conversation_manager": conversation_manager,
        },
    )
    st_sucks_col2.markdown("Turn this on to use conversation history for the model.")
    st_sucks_col2.markdown(
        "*Note: This will not give memory to the tools that do not use it.*"
    )

    # Model settings get saved separately- no on_change event
    st_sucks_col1.number_input(
        "Model Seed Value",
        value=(model_configuration.model_kwargs.get("seed", 500)),
        key=f"{tool_name}_seed",
        on_change=save_model_setting,
        kwargs={
            "model_owner_name": tool_name,
            "conversation_manager": conversation_manager,
        },
    )
    st_sucks_col2.markdown("Set this to a value to seed the model.  ")
    st_sucks_col2.markdown(
        "Same seed values in the same requests will produce more deterministic results."
    )

    response_format_options = ["text", "json_object"]
    response_format_value = model_configuration.model_kwargs.get(
        "response_format", {}
    ).get("type", "text")
    response_format_index = response_format_options.index(response_format_value)

    # Model settings get saved separately- no on_change event
    st_sucks_col1.selectbox(
        "Model Output Type",
        options=response_format_options,
        index=response_format_index,
        key=f"{tool_name}_response_format",
        on_change=save_model_setting,
        kwargs={
            "model_owner_name": tool_name,
            "conversation_manager": conversation_manager,
        },
    )
    st_sucks_col2.markdown(
        "Using the `json_object` response format will return the model output as a JSON object, making tool use and other features more reliable."
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

    configured_completion_tokens = int(model_configuration.max_completion_tokens)

    configured_max_conversation_history_tokens = int(
        model_configuration.max_conversation_history_tokens
    )

    history_tokens = st.slider(
        label="Conversation History Tokens",
        min_value=0,
        max_value=max_supported_tokens,
        value=configured_max_conversation_history_tokens,
        key=f"{tool_name}_conversation_history_tokens",
        disabled=st.session_state[f"{tool_name}_uses_conversation_history"] is False,
        on_change=save_model_setting,
        kwargs={
            "model_owner_name": tool_name,
            "conversation_manager": conversation_manager,
        },
    )

    completion_tokens = st.slider(
        label="Completion Tokens",
        min_value=0,
        max_value=max_model_completion_tokens,
        value=min(configured_completion_tokens, max_model_completion_tokens),
        key=f"{tool_name}_completion_tokens",
        on_change=save_model_setting,
        kwargs={
            "model_owner_name": tool_name,
            "conversation_manager": conversation_manager,
        },
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


def save_slider(session_state_key, conversation_manager: ConversationManager):
    # Get the value of the slider from the session
    slider_value = st.session_state[session_state_key]

    # Save the value to the database
    UserSettings().add_update_user_setting(
        conversation_manager.user_id,
        setting_name=session_state_key,
        setting_value=slider_value,
        available_for_llm=True,
    )


def save_toggle(session_state_key, conversation_manager: ConversationManager):
    # Get the value of the slider from the session
    value = st.session_state[session_state_key]

    # Save the value to the database
    UserSettings().add_update_user_setting(
        conversation_manager.user_id,
        setting_name=session_state_key,
        setting_value=value,
        available_for_llm=True,
    )


def show_additional_settings(
    configuration, tool_name, tool_details, conversation_manager: ConversationManager
):

    if tool_name in configuration["tool_configurations"]:
        # If there are additional settings, get the settings and show the widgets
        if "additional_settings" in configuration["tool_configurations"][tool_name]:
            with st.expander(
                label=f"🦿 {tool_details.display_name} Additional Settings",
                expanded=False,
            ):
                additional_settings = configuration["tool_configurations"][tool_name][
                    "additional_settings"
                ]

                for additional_setting_name in additional_settings:
                    additional_setting = additional_settings[additional_setting_name]
                    session_state_key = f"{tool_name}_{additional_setting_name}"
                    if additional_setting["type"] == "int":
                        int_setting(
                            tool_name,
                            additional_setting_name,
                            additional_setting,
                            session_state_key,
                            conversation_manager=conversation_manager,
                        )
                    elif additional_setting["type"] == "bool":
                        bool_setting(
                            tool_name=tool_name,
                            additional_setting_name=additional_setting_name,
                            additional_setting=additional_setting,
                            session_state_key=session_state_key,
                            conversation_manager=conversation_manager,
                        )

                    st.markdown(additional_setting["description"])


def bool_setting(
    tool_name,
    additional_setting_name,
    additional_setting,
    session_state_key,
    conversation_manager: ConversationManager,
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
            "conversation_manager": conversation_manager,
        },
    )


def int_setting(
    tool_name,
    additional_setting_name,
    additional_setting,
    session_state_key,
    conversation_manager: ConversationManager,
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
            "conversation_manager": conversation_manager,
        },
    )


def show_model_settings(
    tool_name, tool_details, conversation_manager: ConversationManager
):

    setting = UserSettings().get_user_setting(
        conversation_manager.user_id,
        f"{tool_name}_model_configuration",
        default_value=ModelConfiguration.default().model_dump_json(),
    )

    tool_model_configuration = ModelConfiguration(**json.loads(setting.setting_value))

    available_models = ui_shared.get_available_models()

    with st.expander(
        label=f"⚙️ {tool_details.display_name} Model Settings",
        expanded=False,
    ):
        generate_model_settings(
            tool_name=tool_name,
            model_configuration=tool_model_configuration,
            available_models=available_models,
            conversation_manager=conversation_manager,
        )


def tools_settings(conversation_manager: ConversationManager):
    configuration = ui_shared.get_app_configuration()

    tools = get_available_tools(
        configuration=configuration, conversation_manager=conversation_manager
    )

    tool_categories = set(
        [t.structured_tool.func._tool_metadata["category"] for t in tools]
    )

    # reorder tools_categories alphabetically
    tool_categories = sorted(tool_categories)

    st.caption(
        "Tool settings are broken into categories.  Select a category to view the tools in that category.  You can then enable/disable tools and configure their settings.  Settings are saved automatically when you navigate away from the page."
    )

    # Create tabs for each category
    category_tabs = list(tool_categories) + ["Uncategorized"]
    selected_category = st.selectbox("Select Category", category_tabs, index=0)

    # Filter tools by the selected category
    for tool in tools:
        if tool.structured_tool.func._tool_metadata["category"] == selected_category:
            st.markdown(f"#### {tool.display_name}")
            st.markdown(tool.help_text)
            col1, col2, col3 = st.columns([3, 5, 5])
            col1.toggle(
                "Enabled",
                value=ToolManager.is_tool_enabled(
                    conversation_manager=conversation_manager, tool_name=tool.name
                ),
                key=tool.name + "_enabled",
                on_change=save_additional_setting,
                kwargs={
                    "setting_name": tool.name + "_enabled",
                    "session_state_key": tool.name + "_enabled",
                    "conversation_manager": conversation_manager,
                },
            )
            col2.toggle(
                "Return results directly to UI",
                value=ToolManager.should_return_direct(
                    tool_name=tool.name, conversation_manager=conversation_manager
                ),
                help="Occasionally it is useful to have the results returned directly to the UI instead of having the AI re-interpret them, such as when you want to see the raw output of a tool.\n\n*Note: If `return direct` is set, the AI will not perform any tasks after this one completes.*",
                key=f"{tool.name}_return_direct",
                on_change=save_additional_setting,
                kwargs={
                    "setting_name": tool.name + "_return_direct",
                    "session_state_key": f"{tool.name}_return_direct",
                    "conversation_manager": conversation_manager,
                },
            )
            col3.toggle(
                "Include Results in Conversation",
                value=ToolManager.should_include_in_conversation(
                    tool_name=tool.name, conversation_manager=conversation_manager
                ),
                help="When enabled, the results of this tool will be included in the conversation history.\n\n*Turn this on when you want the LLM to always remember results returned for this tool.*",
                key=f"{tool.name}_include_in_conversation",
                on_change=save_additional_setting,
                kwargs={
                    "setting_name": tool.name + "_include_in_conversation",
                    "session_state_key": f"{tool.name}_include_in_conversation",
                    "conversation_manager": conversation_manager,
                },
            )

            # If an LLM is required, show the model configuration settings
            if tool.structured_tool.func._tool_metadata["requires_llm"]:
                show_model_settings(
                    tool_name=tool.name,
                    tool_details=tool,
                    conversation_manager=conversation_manager,
                )
            show_additional_settings(
                configuration=configuration,
                tool_name=tool.name,
                tool_details=tool,
                conversation_manager=conversation_manager,
            )

            st.divider()

    # save_tool_settings(
    #     tools=tools,
    #     configuration=configuration,
    #     selected_category=selected_category,
    #     conversation_manager=conversation_manager,
    # )


def save_tool_settings(
    tools, configuration, selected_category, conversation_manager: ConversationManager
):
    # Iterate through all of the tools and save their settings
    for tool in tools:
        # are we on the tab for this tool?  Might not be displayed.
        if tool.name not in st.session_state:
            continue

        ToolManager.get_tool_category(
            tool_name=tool.name, conversation_manager=conversation_manager
        )

        if selected_category != (
            tool.structured_tool.func._tool_metadata["category"] or "Uncategorized"
        ):
            continue

        # Only save if the settings are different
        needs_saving = False

        enabled = st.session_state[tool.name]
        if enabled != ToolManager.is_tool_enabled(
            conversation_manager=conversation_manager, tool_name=tool.name
        ):
            needs_saving = True

        include_results_in_conversation_history = st.session_state[
            f"{tool.name}_include_in_conversation"
        ]
        if (
            include_results_in_conversation_history
            != ToolManager.should_include_in_conversation(
                tool_name=tool.name, conversation_manager=conversation_manager
            )
        ):
            needs_saving = True

        return_direct = st.session_state[f"{tool.name}_return_direct"]
        if return_direct != ToolManager.should_return_direct(
            conversation_manager=conversation_manager, tool_name=tool.name
        ):
            needs_saving = True

        # see if there are any extra settings to save
        if tool.name in configuration["tool_configurations"]:
            existing_tool_configuration = configuration["tool_configurations"][
                tool.name
            ]

            needs_saving = model_configuration_needs_saving(
                tool.name, existing_tool_configuration, needs_saving
            )
        else:
            model_configuration = None

        if needs_saving:
            st.toast(f"Saving {tool.name} settings...")

            # Save settings to database
            conversation_manager.user_settings_helper.add_update_user_setting(
                user_id=conversation_manager.user_id,
                setting_name=tool.name + "_enabled",
                setting_value=enabled,
                available_for_llm=True,
            )

            conversation_manager.user_settings_helper.add_update_user_setting(
                user_id=conversation_manager.user_id,
                setting_name=tool.name + "_include_in_conversation",
                setting_value=include_results_in_conversation_history,
                available_for_llm=False,
            )

            conversation_manager.user_settings_helper.add_update_user_setting(
                user_id=conversation_manager.user_id,
                setting_name=tool.name + "_return_direct",
                setting_value=return_direct,
                available_for_llm=False,
            )

            if model_configuration:
                UserSettings().add_update_user_setting(
                    conversation_manager.user_id,
                    f"{tool.name}_model_configuration",
                    model_configuration.model_dump_json(),
                )

                # Force a reload of the AI (and conversation manager)
                if "rag_ai" in st.session_state:
                    del st.session_state["rag_ai"]


def model_configuration_needs_saving(
    tool_name, existing_model_configuration: ModelConfiguration, needs_saving
):

    if existing_model_configuration:
        # Get the model configuration from the UI

        model = list(st.session_state[f"{tool_name}_model"])[0]
        if model != existing_model_configuration.model:
            existing_model_configuration.model = model
            needs_saving = True

        uses_conversation_history = st.session_state[
            f"{tool_name}_uses_conversation_history"
        ]

        if (
            uses_conversation_history
            != existing_model_configuration.uses_conversation_history
        ):
            existing_model_configuration.uses_conversation_history = (
                uses_conversation_history
            )
            needs_saving = True

        max_conversation_history_tokens = st.session_state[
            f"{tool_name}_conversation_history_tokens"
        ]
        max_completion_tokens = st.session_state[f"{tool_name}_completion_tokens"]

        if (
            max_conversation_history_tokens
            != existing_model_configuration.max_conversation_history_tokens
        ):
            existing_model_configuration.max_conversation_history_tokens = (
                max_conversation_history_tokens
            )
            needs_saving = True
        if max_completion_tokens != existing_model_configuration.max_completion_tokens:
            existing_model_configuration.max_completion_tokens = max_completion_tokens
            needs_saving = True
        max_retries = st.session_state[f"{tool_name}_max_retries"]
        if max_retries != existing_model_configuration.max_retries:
            existing_model_configuration.max_retries = max_retries
            needs_saving = True

        temperature = st.session_state[f"{tool_name}_temperature"]
        if temperature != existing_model_configuration.temperature:
            existing_model_configuration.temperature = temperature
            needs_saving = True

        seed = st.session_state[f"{tool_name}_seed"]
        existing_seed = existing_model_configuration.model_kwargs.get("seed", None)
        if (existing_seed is None and seed) or (
            existing_seed and seed != existing_seed
        ):
            existing_model_configuration.model_kwargs["seed"] = seed
            needs_saving = True

        response_format_type = st.session_state[f"{tool_name}_response_format"]
        existing_response_format_type = existing_model_configuration.model_kwargs.get(
            "response_format", None
        )
        existing_response_format_type = (
            existing_response_format_type.get("type", None)
            if existing_response_format_type
            else None
        )
        if (existing_response_format_type is None and response_format_type) or (
            existing_response_format_type
            and response_format_type != existing_response_format_type
        ):
            existing_model_configuration.model_kwargs["response_format"] = {
                "type": response_format_type
            }
            needs_saving = True

    return needs_saving


def save_jama_settings_to_file(
    jama_api_url,
    jama_client_id,
    jama_client_secret,
    conversation_manager: ConversationManager,
):
    user_settings_helper = UserSettings()
    user_id = conversation_manager.user_id

    user_settings_helper.add_update_user_setting(
        user_id=user_id,
        setting_name="jama_api_url",
        setting_value=jama_api_url,
        available_for_llm=False,
    )

    user_settings_helper.add_update_user_setting(
        user_id=user_id,
        setting_name="jama_client_id",
        setting_value=jama_client_id,
        available_for_llm=False,
    )

    user_settings_helper.add_update_user_setting(
        user_id=user_id,
        setting_name="jama_client_secret",
        setting_value=jama_client_secret,
        available_for_llm=False,
    )

    st.success("Jama settings saved successfully!")


def save_jarvis_settings(
    jarvis_ai_model_configuration: ModelConfiguration,
    file_ingestion_model_configuration: ModelConfiguration,
    conversation_manager: ConversationManager,
):
    # Save to user settings
    user_settings_helper = UserSettings()

    user_settings_helper.add_update_user_setting(
        user_id=conversation_manager.user_id,
        setting_name="jarvis_ai_model_configuration",
        setting_value=jarvis_ai_model_configuration.model_dump_json(),
        available_for_llm=True,
    )

    user_settings_helper.add_update_user_setting(
        user_id=conversation_manager.user_id,
        setting_name="file_ingestion_model_configuration",
        setting_value=file_ingestion_model_configuration.model_dump_json(),
        available_for_llm=True,
    )

    # Force a reload of the AI (and conversation manager)
    if "rag_ai" in st.session_state:
        del st.session_state["rag_ai"]
        

def save_jarvis_voice_settings(
    jarvis_ai_model_configuration: ModelConfiguration,
    conversation_manager: ConversationManager,
):
    # Save to user settings
    user_settings_helper = UserSettings()

    user_settings_helper.add_update_user_setting(
        user_id=conversation_manager.user_id,
        setting_name="jarvis_ai_model_configuration",
        setting_value=jarvis_ai_model_configuration.model_dump_json(),
        available_for_llm=True,
    )    

    # Force a reload of the AI (and conversation manager)
    if "rag_ai" in st.session_state:
        del st.session_state["rag_ai"]        


def save_model_setting(model_owner_name, conversation_manager: ConversationManager):
    # Get all of the preset settings for the model (e.g. max tokens, etc.)
    model_friendly_name = st.session_state[f"{model_owner_name}_model"][
        list(st.session_state[f"{model_owner_name}_model"])[0]
    ]
    max_model_supported_tokens = int(
        ui_shared.get_available_models()[model_friendly_name]["model_configuration"][
            "max_model_supported_tokens"
        ]
    )
    llm_type = ui_shared.get_available_models()[model_friendly_name][
        "model_configuration"
    ]["llm_type"]

    model = list(st.session_state[f"{model_owner_name}_model"])[0]
    temperature = st.session_state[f"{model_owner_name}_temperature"]
    max_retries = st.session_state[f"{model_owner_name}_max_retries"]
    uses_conversation_history = st.session_state[
        f"{model_owner_name}_uses_conversation_history"
    ]
    max_conversation_history_tokens = st.session_state[
        f"{model_owner_name}_conversation_history_tokens"
    ]
    max_completion_tokens = st.session_state[f"{model_owner_name}_completion_tokens"]
    model_kwargs = {
        "seed": st.session_state[f"{model_owner_name}_seed"],
        "response_format": {
            "type": st.session_state[f"{model_owner_name}_response_format"]
        },
    }

    updated_model_config = ModelConfiguration(
        llm_type=llm_type,
        model=model,
        temperature=temperature,
        max_retries=max_retries,
        max_model_supported_tokens=max_model_supported_tokens,
        uses_conversation_history=uses_conversation_history,
        max_conversation_history_tokens=max_conversation_history_tokens,
        max_completion_tokens=max_completion_tokens,
        model_kwargs=model_kwargs,
    )

    UserSettings().add_update_user_setting(
        conversation_manager.user_id,
        setting_name=(model_owner_name + "_model_configuration"),
        setting_value=updated_model_config.model_dump_json(),
        available_for_llm=True,
    )

    # Force a reload of the AI (and conversation manager)
    if "rag_ai" in st.session_state:
        del st.session_state["rag_ai"]


def save_additional_setting(
    setting_name,
    session_state_key,
    conversation_manager: ConversationManager,
    tool_name=None,
):

    value = st.session_state[session_state_key]

    UserSettings().add_update_user_setting(
        conversation_manager.user_id,
        setting_name=(tool_name + "_" + setting_name) if tool_name else setting_name,
        setting_value=value,
        available_for_llm=True,
    )

    # Force a reload of the AI (and conversation manager)
    if "rag_ai" in st.session_state:
        del st.session_state["rag_ai"]


def general_settings():
    # Debug Logging
    logging_options = ["DEBUG", "INFO", "WARN"]
    debug_logging = st.selectbox(
        "Logging Level",
        logging_options,
        index=logging_options.index(os.getenv("LOGGING_LEVEL", "INFO")),
    )

    st.caption(
        "Set the logging level for the application.  Debug is the most detailed, and should be used for troubleshooting."
    )

    # Save button
    if st.button("Save Settings"):
        os.environ["LOGGING_LEVEL"] = str(debug_logging)
        logging.basicConfig(level=debug_logging)


def source_control_provider_form():
    st.subheader("Manage Source Control Providers")
    code_helper = Code()

    # Initialize current_operation if it doesn't exist
    if "current_operation" not in st.session_state:
        st.session_state["current_operation"] = None

    existing_providers = code_helper.get_all_source_control_providers()

    # Only show these buttons if no operation has been selected yet
    if st.session_state["current_operation"] is None:
        if st.button("New Source Control Provider"):
            st.session_state["current_operation"] = "add"

        elif existing_providers:  # Only show edit/delete if there are providers
            provider_names = [
                p.source_control_provider_name for p in existing_providers
            ]
            st.selectbox(
                "Select an existing provider", provider_names, key="existing_provider"
            )

            col1, col2 = st.columns(2)

            col1.button(
                "Edit Source Control Provider",
                on_click=set_source_control_operation,
                kwargs={"operation_type": "edit"},
            )
            col2.button(
                "Delete Source Control Provider",
                on_click=set_source_control_operation,
                kwargs={"operation_type": "delete"},
            )

    # Now handle each operation separately
    if st.session_state["current_operation"] == "add":
        add_provider_form(code_helper)

    elif st.session_state["current_operation"] == "edit":
        selected_provider = get_selected_provider(existing_providers)
        if selected_provider:
            edit_provider_form(selected_provider, code_helper)

    elif st.session_state["current_operation"] == "delete":
        # Confirm before deleting
        selected_provider = get_selected_provider(existing_providers)
        if selected_provider:
            st.button(
                f"Confirm Deletion of '{selected_provider.source_control_provider_name}'",
                on_click=delete_provider,
                kwargs={
                    "code_helper": code_helper,
                    "selected_provider": selected_provider,
                },
            )


def set_source_control_operation(operation_type: str):
    st.session_state["current_operation"] = operation_type


def delete_provider(code_helper: Code, selected_provider: SourceControlProviderModel):
    code_helper.delete_source_control_provider(selected_provider.id)
    st.success("Provider deleted successfully!")
    # Reset current operation after deletion
    st.session_state["current_operation"] = None


def get_selected_provider(existing_providers):
    return next(
        (
            p
            for p in existing_providers
            if p.source_control_provider_name == st.session_state["existing_provider"]
        ),
        None,
    )


def add_or_edit_cancel_button():
    # Shared cancel button for add/edit forms
    st.form_submit_button(
        "Cancel", on_click=lambda: st.session_state.pop("current_operation")
    )


def add_provider_form(code_helper: Code):
    # Form for adding a new provider
    with st.form("add_provider_form"):
        st.selectbox(
            "Provider",
            [s.name for s in code_helper.get_supported_source_control_providers()],
            key="supported_provider_name",
        )
        st.text_input(
            "Name", key="name", help="Enter a friendly name for this provider."
        )
        st.text_input(
            "URL", key="url", help="Enter the URL of the API for this provider."
        )
        st.caption(
            "Make sure you enter the correct URL for the API of this provider.  i.e., for GitHub, it would be 'https://api.github.com'."
        )
        use_auth = st.checkbox(
            "Requires Authentication",
            key="requires_auth",
            help="Check this box if the provider requires authentication.",
        )
        st.text_input("Access Token", key="access_token")

        col1, col2 = st.columns(2)
        with col1:
            add_or_edit_cancel_button()
        with col2:
            st.form_submit_button(
                "Add Provider",
                on_click=add_update_provider,
                kwargs={"code_helper": code_helper},
            )


def add_update_provider(
    code_helper: Code, existing_provider: SourceControlProviderModel = None
):
    # Get the provider ID from the name
    supported_provider = code_helper.get_supported_source_control_provider_by_name(
        st.session_state["supported_provider_name"]
    )

    # Is this an update or a new provider?
    if existing_provider:
        code_helper.update_source_control_provider(
            id=existing_provider.id,
            supported_source_control_provider=supported_provider,
            name=st.session_state["name"],
            url=st.session_state["url"],
            requires_auth=st.session_state["requires_auth"],
            access_token=st.session_state["access_token"],
        )
        st.success("Provider updated successfully!")

    else:
        code_helper.add_source_control_provider(
            supported_provider,
            name=st.session_state["name"],
            url=st.session_state["url"],
            requires_auth=st.session_state["requires_auth"],
            access_token=st.session_state["access_token"],
        )
        st.success("Provider added successfully!")

    st.session_state["current_operation"] = None


def edit_provider_form(
    existing_provider: SourceControlProviderModel, code_helper: Code
):
    # Form for editing an existing provider
    with st.form("edit_provider_form"):
        supported_providers = code_helper.get_supported_source_control_providers()
        index = 0

        for i, supported_provider in enumerate(supported_providers):
            if (
                supported_provider.id
                == existing_provider.supported_source_control_provider_id
            ):
                index = i
                break

        st.selectbox(
            "Provider",
            [s.name for s in supported_providers],
            index=index,
            key="supported_provider_name",
        )
        st.text_input(
            "Name",
            value=existing_provider.source_control_provider_name,
            key="name",
            help="Enter a friendly name for this provider.",
        )
        st.text_input(
            "URL",
            value=existing_provider.source_control_provider_url,
            key="url",
            help="Enter the URL of the API for this provider. (e.g., 'https://api.github.com')",
        )
        use_auth = st.checkbox(
            "Requires Authentication",
            value=existing_provider.requires_authentication,
            help="Check this box if the provider requires authentication.",
            key="requires_auth",
        )
        st.text_input(
            "Access Token",
            value=existing_provider.source_control_access_token,
            key="access_token",
        )

        col1, col2 = st.columns(2)
        with col1:
            add_or_edit_cancel_button()
        with col2:
            st.form_submit_button(
                "Update Provider",
                on_click=add_update_provider,
                kwargs={
                    "code_helper": code_helper,
                    "existing_provider": existing_provider,
                },
            )


# Run the settings page
if __name__ == "__main__":
    try:
        ensure_authenticated()
        
        user_email = os.environ.get("USER_EMAIL", None)
        if ui_shared.ensure_user(user_email):
            settings_page(user_email)
    except:
        # This whole thing is dumb as shit, and I don't know why python is like this... maybe I'm just a noob.
        # Check to see if the type of exception is a "StopException",
        # which gets thrown when a user navigates away from a page while the debugger is attached.
        # But we don't have access to that type, so we have to check the string.  Dumb.

        # Get the last exception
        exc_type, exc_value, exc_traceback = sys.exc_info()

        if "StopException" in str(
            exc_value.__class__
        ) or "StreamlitAPIException" in str(exc_value.__class__):
            # If so, then just return
            pass
        else:
            # Otherwise, raise the exception
            raise

import json
import logging
import os
import sys
import time
import uuid

import streamlit as st
from streamlit_extras.stylable_container import stylable_container


from src.configuration.assistant_configuration import (
    ApplicationConfigurationLoader,
)

from src.ai.rag_ai import RetrievalAugmentedGenerationAI
from src.configuration.model_configuration import ModelConfiguration
from src.db.models.user_settings import UserSettings
from src.db.models.users import Users

import src.ui.streamlit_shared as ui_shared

from src.ai.prompts.prompt_manager import PromptManager

from src.utilities.configuration_utilities import get_app_configuration


class RagUI:

    def __init__(self, user_email: str = None):
        self.user_email = user_email
        self.prompt_manager = None

    def load_configuration(self):
        """Loads the configuration from the path"""

        if "app_config" not in st.session_state:
            st.session_state["app_config"] = get_app_configuration()

    def set_page_config(self):
        """Sets the page configuration"""
        st.set_page_config(
            page_title="Jarvis - Retrieval Augmented Generation AI",
            page_icon="📖",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        st.title("Hey Jarvis 🤖...")

    def load_ai(self, override_conversation_id=None):
        """Loads the AI instance for the selected conversation id"""

        if override_conversation_id:
            selected_conversation_id = override_conversation_id
        else:
            selected_conversation_id = ui_shared.get_selected_conversation_id()

        user = Users().get_user_by_email(user_email)

        if "rag_ai" not in st.session_state:
            # Reload the prompt manager
            self.set_prompt_manager(user)

            # First time loading the page
            logging.debug("load_ai: no ai in session state, creating a new one")
            rag_ai_instance = RetrievalAugmentedGenerationAI(
                configuration=st.session_state["app_config"],
                conversation_id=selected_conversation_id,
                user_email=self.user_email,
                streaming=True,
                prompt_manager=self.prompt_manager,
            )
            st.session_state["rag_ai"] = rag_ai_instance
            logging.debug("load_ai: created new ai instance")

        elif selected_conversation_id and selected_conversation_id != str(
            st.session_state["rag_ai"].conversation_manager.conversation_id
        ):
            # Reload the prompt manager
            self.set_prompt_manager(user)

            logging.debug(
                f"load_ai: AI instance exists, but need to change conversation ID from {str(st.session_state['rag_ai'].conversation_manager.conversation_id)} to {selected_conversation_id}"
            )
            # We have an AI instance, but we need to change the conversation (conversation) id
            rag_ai_instance = RetrievalAugmentedGenerationAI(
                configuration=st.session_state["app_config"],
                conversation_id=selected_conversation_id,
                user_email=self.user_email,
                streaming=True,
                prompt_manager=self.prompt_manager,
            )
            st.session_state["rag_ai"] = rag_ai_instance
        else:
            logging.debug(
                "load_ai: AI instance exists, no need to change conversation ID"
            )

    def set_prompt_manager(self, user):
        jarvis_ai_model_configuration = ModelConfiguration(
            **json.loads(
                UserSettings()
                .get_user_setting(
                    user.id,
                    "jarvis_ai_model_configuration",
                    default_value=ModelConfiguration.default().model_dump_json(),
                )
                .setting_value
            )
        )

        self.prompt_manager = PromptManager(
            llm_type=jarvis_ai_model_configuration.llm_type
        )

    def create_collections_container(self, main_window_container):
        css_style = """{
    position: fixed;     /* Keeps the element fixed on the screen */
    top: 140px;              /* Aligns the element to the top of the screen */
    right: 50px;         /* Adjust the right position as needed */
    max-width: 100%;     /* Ensures the element width doesn't exceed area */
    z-index: 9999;       /* Ensures the element is on top of other content */
    max-height: calc(100vh - 280px); /* Sets the maximum height to 100% of viewport height minus 140px */
    overflow: auto;      /* Adds a scrollbar when the content overflows */
    overflow-x: hidden;  /* Hides horizontal scrollbar */
}
"""

        with main_window_container:
            with stylable_container(key="collections_container", css_styles=css_style):
                if "rag_ai" in st.session_state:

                    logging.debug("Creating collection selectbox")
                    ui_shared.create_documents_and_code_collections(
                        ai=st.session_state["rag_ai"]
                    )

                    if "rag_ai" in st.session_state:
                        collection_id = ui_shared.get_selected_collection_id()
                        if collection_id != -1:
                            loaded_docs_delimited = None
                            st.session_state.rag_ai.conversation_manager.collection_id = (
                                collection_id
                            )

                            loaded_docs_delimited = (
                                st.session_state.rag_ai.conversation_manager.get_loaded_documents_delimited()
                            )

                            st.divider()
                            st.markdown("#### Options")

                            search_type = UserSettings().get_user_setting(
                                user_id=st.session_state.user_id,
                                setting_name="search_type",
                                default_value="Hybrid",
                                default_available_for_llm=True,
                            )
                            search_top_k = UserSettings().get_user_setting(
                                user_id=st.session_state.user_id,
                                setting_name="search_top_k",
                                default_value=10,
                                default_available_for_llm=True,
                            )

                            with st.expander(
                                "Search", expanded=False
                            ):  # , expanded=expanded):
                                search_types = ["Similarity", "Keyword", "Hybrid"]
                                st.radio(
                                    label="Text search method",
                                    help="Similarity search will find semantically similar phrases.\n\nKeyword search (think SQL LIKE statement) will find documents containing specific words.\n\nHybrid search uses both.",
                                    options=search_types,
                                    key="search_type",
                                    index=search_types.index(search_type.setting_value),
                                    on_change=ui_shared.save_user_setting,
                                    kwargs={
                                        "setting_name": "search_type",
                                        "available_for_llm": search_type.available_for_llm,
                                    },
                                )
                                st.number_input(
                                    "Top K (number of document chunks to use in searches)",
                                    key="search_top_k",
                                    help="The number of document chunks to use in searches. Higher numbers will take longer to search, but will possibly yield better results.  Note: a higher number will use more of the model's context window.",
                                    value=int(search_top_k.setting_value),
                                    on_change=ui_shared.save_user_setting,
                                    step=1,
                                    kwargs={
                                        "setting_name": "search_top_k",
                                        "available_for_llm": search_top_k.available_for_llm,
                                    },
                                )

                            with st.expander("Advanced"):
                                options = []
                                if loaded_docs_delimited:
                                    options = [d for d in loaded_docs_delimited]

                                options.insert(0, "0:---")

                                st.selectbox(
                                    "Override automatic document selection:",
                                    help="Select a document from the list below to override the AI's document selection.\n\nThis will force the AI to use the selected document for all responses.",
                                    options=options,
                                    key="override_file",
                                    format_func=lambda x: x.split(":")[1],
                                )
                                st.number_input(
                                    "Timeout (seconds)",
                                    help="The amount of time to wait for a response from the AI",
                                    key="agent_timeout",
                                    value=600,
                                )

                                st.number_input(
                                    "Maximum AI iterations",
                                    help="The number of recursive (or other) iterations the AI will perform (usually tool calls).",
                                    key="max_iterations",
                                    value=25,
                                )
                        else:
                            st.warning("No collection selected")

            st.write("")
            st.write("")
            st.write("")
            st.write("")
            st.write("")
            st.write("")


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOGGING_LEVEL", "INFO"))

    try:
        logging.debug("Starting Jarvis")
        # Get the user from the environment variables
        user_email = os.environ.get("USER_EMAIL", None)
        logging.debug(f"User email: {user_email}")

        # Time the operation
        start_time = time.time()
        rag_ui = RagUI(user_email=user_email)
        logging.info(f"Time to load RagUI: {time.time() - start_time}")

        # Always comes first!
        logging.debug("Loading configuration")
        # Time the operation
        start_time = time.time()
        rag_ui.load_configuration()
        logging.info(f"Time to load configuration: {time.time() - start_time}")

        logging.debug("Setting page config")
        # Time the operation
        start_time = time.time()
        rag_ui.set_page_config()
        logging.info(f"Time to set page config: {time.time() - start_time}")

        if not user_email:
            raise ValueError("USER_EMAIL environment variable not set")

        logging.debug("Ensuring user exists")
        # Time the operation
        start_time = time.time()
        if ui_shared.ensure_user(user_email):
            logging.info(f"Time to ensure user exists: {time.time() - start_time}")

            logging.debug("User exists")

            # Time the operation
            start_time = time.time()
            ui_shared.set_user_id_from_email(user_email)
            logging.info(f"Time to set user id from email: {time.time() - start_time}")

            # Time the operation
            start_time = time.time()
            ui_shared.ensure_conversation()
            logging.info(f"Time to ensure conversation: {time.time() - start_time}")

            conversations, files_and_settings = st.sidebar.tabs(
                ["Conversations", "Files & Settings"]
            )

            # Time the operation
            start_time = time.time()
            ui_shared.load_conversation_selectbox(rag_ui.load_ai, conversations)
            logging.info(
                f"Time to load conversation selectbox: {time.time() - start_time}"
            )

            # Set up columns for chat and collections
            col1, col2 = st.columns([0.65, 0.35])

            # Time the operation
            start_time = time.time()
            rag_ui.load_ai()
            logging.info(f"Time to load AI: {time.time() - start_time}")

            # Time the operation
            start_time = time.time()
            rag_ui.create_collections_container(col2)
            logging.info(
                f"Time to create collections container: {time.time() - start_time}"
            )

            # Time the operation
            start_time = time.time()
            ui_shared.select_documents(
                ai=st.session_state["rag_ai"], tab=files_and_settings
            )
            logging.info(f"Time to select documents: {time.time() - start_time}")

            # Time the operation
            start_time = time.time()
            ui_shared.handle_chat(col1, st.session_state["rag_ai"])
            logging.info(f"Time to handle chat: {time.time() - start_time}")

            # Time the operation
            start_time = time.time()
            ui_shared.show_version()
            logging.info(f"Time to show version: {time.time() - start_time}")
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

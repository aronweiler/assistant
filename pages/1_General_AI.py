import logging
import uuid
import shutil
import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.grid import grid
import os

from langchain.callbacks.streamlit import StreamlitCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler

from src.ai.request_router import RequestRouter

from src.configuration.assistant_configuration import AssistantConfigurationLoader


from src.db.models.interactions import Interactions
from src.db.models.documents import Documents
from src.db.models.users import Users
from src.db.models.domain.file_model import FileModel
from src.db.models.domain.document_model import DocumentModel

from src.documents.document_loader import load_and_split_documents

# from src.runners.ui.streamlit_agent_callback import StreamlitAgentCallbackHandler

from src.ai.llm_helper import get_prompt
from src.utilities.hash_utilities import calculate_sha256
from src.ai.callbacks.streamlit_callbacks import StreamingOnlyCallbackHandler

import src.ui.streamlit_shared as ui_shared


class GeneralUI:
    def __init__(self):
        self.user_email = None

    def get_configuration_path(self):
        return os.environ.get(
            "ASSISTANT_CONFIG_PATH",
            "configurations/console_configs/console_ai.json",
        )

    def create_collections_container(self, main_window_container):
        css_style = """{
    position: fixed;  /* Keeps the element fixed on the screen */
    top: 10px;        /* Adjust the top position as needed */
    right: 10px;      /* Adjust the right position as needed */
    width: 300px;     /* Adjust the width as needed */
    max-width: 100%;  /* Ensures the element width doesn't exceed area */
    z-index: 9999;    /* Ensures the element is on top of other content */
    max-height: 80vh;     /* Sets the maximum height to 90% of the viewport height */
    overflow: auto;     /* Adds a scrollbar when the content overflows */
    overflow-x: hidden;   /* Hides horizontal scrollbar */
}"""

        selected_interaction_id = ui_shared.get_selected_interaction_id()

        with main_window_container:
            with stylable_container(key="collections_container", css_styles=css_style):
                if "general_ai" in st.session_state:
                    st.caption("Selected document collection:")
                    # This is a hack, but it works
                    col1, col2 = st.columns([0.80, 0.2])
                    col1.selectbox(
                        "Active document collection",
                        ui_shared.get_available_collections(selected_interaction_id),
                        key="active_collection",
                        label_visibility="collapsed",
                    )

                    with st.container():
                        col1, col2 = st.columns(2)
                        col1.text_input(
                            "Collection name",
                            key="new_collection_name",
                            label_visibility="collapsed",
                        )
                        new_collection = col2.button(
                            "Create New", key="create_collection"
                        )

                        if (
                            st.session_state.get("new_collection_name")
                            and new_collection
                        ):
                            ui_shared.create_collection(
                                st.session_state["new_collection_name"]
                            )
                            st.experimental_rerun()

                    if "general_ai" in st.session_state:
                        option = st.session_state["active_collection"]
                        if option:
                            collection_id = ui_shared.collection_id_from_option(
                                option, selected_interaction_id
                            )

                            st.session_state[
                                "general_ai"
                            ].interaction_manager.collection_id = collection_id

                            loaded_docs = st.session_state[
                                "general_ai"
                            ].interaction_manager.get_loaded_documents_for_display()

                            with st.expander("File Search Options", expanded=False):
                                st.text_input("Top K", key="search_top_k", value=10)

                            with st.expander(
                                label=f"({len(loaded_docs)}) documents in {option}",
                                expanded=False,
                            ):
                                for doc in loaded_docs:
                                    st.write(doc)
                            # col1, col2 = expander.columns(2)
                            # for doc in loaded_docs:
                            #     col1.write(doc)
                            #     col2.button("Delete", key=f"delete_{doc}")
                        else:
                            st.warning("No collection selected")

            # st.write("")
            # st.write("")
            # st.write("")
            # st.write("")
            # st.write("")
            # st.write("")

    def load_ai(self):
        """Loads the AI instance for the selected interaction id"""
        selected_interaction_id = ui_shared.get_selected_interaction_id()

        if "general_ai" not in st.session_state:
            # First time loading the page
            print("load_ai: ai not in session state")
            general_ai_instance = RequestRouter(
                st.session_state["general_config"],
                self.user_email,
                selected_interaction_id,
                streaming=True,
            )
            st.session_state["general_ai"] = general_ai_instance

        elif selected_interaction_id and selected_interaction_id != str(
            st.session_state["general_ai"].interaction_manager.interaction_id
        ):
            # We have an AI instance, but we need to change the interaction id
            print(
                "load_ai: interaction id is not none and not equal to ai interaction id"
            )
            general_ai_instance = RequestRouter(
                st.session_state["general_config"],
                self.user_email,
                selected_interaction_id,
                streaming=True,
            )
            st.session_state["general_ai"] = general_ai_instance

    def refresh_messages_session_state(self, general_ai_instance):
        """Pulls the messages from the token buffer on the AI for the first time, and put them into the session state"""

        buffer_messages = (
            general_ai_instance.interaction_manager.conversation_token_buffer_memory.buffer_as_messages
        )

        print(f"Length of messages retrieved from AI: {str(len(buffer_messages))}")

        st.session_state["messages"] = []

        for message in buffer_messages:
            if message.type == "human":
                st.session_state["messages"].append(
                    {"role": "user", "content": message.content, "avatar": "🗣️"}
                )
            else:
                st.session_state["messages"].append(
                    {"role": "assistant", "content": message.content, "avatar": "🤖"}
                )

        # with st.chat_message("user", avatar="👤"):
        #             st.markdown(m.content)

        #  = general_ai_instance.interaction_manager.conversation_token_buffer_memory.buffer_as_messages

        # for (
        #     m
        # ) in (
        #     general_ai_instance.interaction_manager.postgres_chat_message_history.messages
        # ):

    def show_old_messages(self, general_ai_instance):
        self.refresh_messages_session_state(general_ai_instance)

        for message in st.session_state["messages"]:
            with st.chat_message(message["role"], avatar=message["avatar"]):
                st.markdown(message["content"])

    # TODO: Replace the DB backed chat history with a cached one here!
    def handle_chat(self, main_window_container):
        with main_window_container.container():
            # Get the AI instance from session state
            if "general_ai" not in st.session_state:
                st.warning("No AI instance found in session state")
                st.stop()
            else:
                general_ai_instance = st.session_state["general_ai"]

            self.show_old_messages(general_ai_instance)

            # st.write("")
            # st.write("")
            # st.write("")
            # st.write("")
            # st.write("")
            # st.write("")

        # Get user input (must be outside of the container)
        prompt = st.chat_input("Enter your message here", key="chat_input")

        if prompt:            
            with main_window_container.container():
                st.chat_message("user", avatar="👤").markdown(prompt)

                with st.chat_message("assistant", avatar="🤖"):
                    agent_callback_container = st.container().empty()
                    llm_container = st.container().empty()
                    llm_callbacks = []
                    llm_callbacks.append(StreamingOnlyCallbackHandler(llm_container))

                    agent_callbacks = []                    
                    print("showing agent thoughts")                    
                    agent_callback = StreamlitCallbackHandler(
                        agent_callback_container,
                        expand_new_thoughts=True,
                        collapse_completed_thoughts=True,
                    )
                    agent_callbacks.append(agent_callback)

                    collection_id = ui_shared.collection_id_from_option(
                        st.session_state["active_collection"],
                        general_ai_instance.interaction_manager.interaction_id,
                    )

                    kwargs = {
                        "search_top_k": int(st.session_state["search_top_k"])
                        if "search_top_k" in st.session_state
                        else 10
                    }

                    result = general_ai_instance.query(
                        prompt,
                        collection_id=collection_id,
                        llm_callbacks=llm_callbacks,
                        agent_callbacks=agent_callbacks,
                        kwargs=kwargs,
                    )

                    print(f"Result: {result}")

                    llm_container.markdown(result)
                    ui_shared.scroll_to_bottom('column')

    def load_configuration(self):
        # Load environment variables from the .env file
        # load_dotenv("/Repos/assistant/.env")

        assistant_config_path = self.get_configuration_path()
        if "general_config" not in st.session_state:
            st.session_state["general_config"] = AssistantConfigurationLoader.from_file(
                assistant_config_path
            )

    def set_page_config(self):
        st.set_page_config(
            page_title="Jarvis - General",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        st.title("Hey Jarvis 🤖...")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    try:
        general_ui = GeneralUI()

        # Always comes first!
        general_ui.load_configuration()

        general_ui.set_page_config()

        # Get the user from the environment variables
        user_email = os.environ.get("USER_EMAIL", None)
        general_ui.user_email = user_email

        if not user_email:
            raise ValueError("USER_EMAIL environment variable not set")

        if ui_shared.ensure_user(user_email):
            ui_shared.set_user_id_from_email(user_email)
            ui_shared.ensure_interaction()
            ui_shared.load_interaction_selectbox(general_ui.load_ai)
            # Set up columns for chat and collections
            col1, col2 = st.columns([0.65, 0.35])

            general_ui.load_ai()
            ui_shared.setup_new_chat_button()
            general_ui.create_collections_container(col2)

            ui_shared.select_documents()

            general_ui.handle_chat(col1)

            ui_shared.scroll_to_bottom('column')

            ui_shared.show_version()
    
    except Exception as e:
        # This should only be catching a StopException thrown by streamlit, yet I cannot find it for the fucking life of me.
        # And after wasting 20 minutes of my life on this, I am done.
        pass
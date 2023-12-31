import logging
import os
import uuid

import streamlit as st
from streamlit_extras.stylable_container import stylable_container


from src.configuration.assistant_configuration import (
    ApplicationConfigurationLoader,
)

from src.ai.rag_ai import RetrievalAugmentedGenerationAI

import src.ui.streamlit_shared as ui_shared

from src.ai.prompts.prompt_manager import PromptManager

from src.utilities.configuration_utilities import get_app_configuration


class RagUI:
    def __init__(self, user_email: str = None):
        self.user_email = user_email

    def load_configuration(self):
        """Loads the configuration from the path"""
        
        if "app_config" not in st.session_state:
            st.session_state["app_config"] = get_app_configuration()
                    
        self.prompt_manager = PromptManager(
            llm_type=st.session_state.app_config['jarvis_ai']['model_configuration']['llm_type']
        )

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

        if "rag_ai" not in st.session_state:
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
            logging.debug("load_ai: AI instance exists, no need to change conversation ID")

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
                    ui_shared.create_documents_and_code_collections(ai=st.session_state["rag_ai"])

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

                            with st.expander("Search", expanded=False):  # , expanded=expanded):
                                search_types = ["Similarity", "Keyword", "Hybrid"]
                                st.radio(
                                    label="Text search method",
                                    help="Similarity search will find semantically similar phrases.\n\nKeyword search (think SQL LIKE statement) will find documents containing specific words.\n\nHybrid search uses both.",
                                    options=search_types,
                                    key="search_type",                                    
                                    index=search_types.index(st.session_state["app_config"]["jarvis_ai"].get("search_type", "Similarity")),
                                    on_change=ui_shared.set_search_type,
                                )
                                st.number_input(
                                    "Top K (number of document chunks to use in searches)",
                                    key="search_top_k",
                                    help="The number of document chunks to use in searches. Higher numbers will take longer to search, but will possibly yield better results.  Note: a higher number will use more of the model's context window.",
                                    value=st.session_state["app_config"]["jarvis_ai"].get("search_top_k", 10),
                                    on_change=ui_shared.set_search_top_k,
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
                                    "Timeout (seconds)", help="The amount of time to wait for a response from the AI", key="agent_timeout", value=600
                                )
                                
                                st.toggle(
                                    "Use Pandas for Spreadsheets",
                                    key="use_pandas",
                                    value=True,
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
        
        rag_ui = RagUI(user_email=user_email)

        # Always comes first!
        logging.debug("Loading configuration")
        rag_ui.load_configuration()

        logging.debug("Setting page config")
        rag_ui.set_page_config()        

        if not user_email:
            raise ValueError("USER_EMAIL environment variable not set")

        logging.debug("Ensuring user exists")
        if ui_shared.ensure_user(user_email):
            logging.debug("User exists")
            ui_shared.set_user_id_from_email(user_email)
            ui_shared.ensure_conversation()

            conversations, files_and_settings = st.sidebar.tabs(
                ["Conversations", "Files & Settings"]
            )

            ui_shared.load_conversation_selectbox(rag_ui.load_ai, conversations)
            # Set up columns for chat and collections
            col1, col2 = st.columns([0.65, 0.35])

            rag_ui.load_ai()
            rag_ui.create_collections_container(col2)

            ui_shared.select_documents(
                ai=st.session_state["rag_ai"], tab=files_and_settings
            )

            ui_shared.handle_chat(col1, st.session_state["rag_ai"], st.session_state["app_config"])

            ui_shared.show_version()            
    except Exception as e:
        # This should only be catching a StopException thrown by streamlit, yet I cannot find it for the fucking life of me.
        # And after wasting 20 minutes of my life on this, I am done.

        logging.error(f"Caught a general exception: {e}")
        st.error(f"Caught a general exception: {e}")

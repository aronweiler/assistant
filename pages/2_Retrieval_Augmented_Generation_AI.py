import streamlit as st
from streamlit_extras.stylable_container import stylable_container
import logging
import os
import sys
import uuid

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfigurationLoader,
)

from src.ai.rag_ai import RetrievalAugmentedGenerationAI

from src.db.models.users import Users
from src.db.models.interactions import Interactions
from src.db.models.documents import Documents


class RagUI:
    def __init__(self):
        self.users_helper = Users()
        self.interaction_helper = Interactions()
        self.documents_helper = Documents()

    def load_configuration(self):
        """Loads the configuration from the path"""
        rag_config_path = os.environ.get(
            "RAG_CONFIG_PATH",
            "configurations/rag_configs/openai_rag.json",
        )

        if "config" not in st.session_state:
            st.session_state[
                "config"
            ] = RetrievalAugmentedGenerationConfigurationLoader.from_file(
                rag_config_path
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

    def ensure_user(self, email):
        """Ensures that a user exists for the given email"""
        self.user_email = email

        user = self.users_helper.get_user_by_email(self.user_email)

        if not user:
            st.markdown(f"Welcome to Jarvis, {self.user_email}! Let's get you set up.")

            # Create the user by showing them a prompt to enter their name, location, age
            name = st.text_input("Enter your name")
            location = st.text_input("Enter your location")

            if st.button("Create Your User!") and name and location:
                user = self.users_helper.create_user(
                    email=self.user_email, name=name, location=location, age=999
                )
                st.experimental_rerun()
            else:
                return False

        else:
            return True

    def set_user_id_from_email(self, user_email):
        """Sets the user_id in the session state from the user's email"""
        users_helper = Users()

        user = users_helper.get_user_by_email(user_email)
        st.session_state["user_id"] = user.id

    def create_interaction(self, interaction_summary):
        """Creates an interaction for the current user with the specified summary"""
        self.interaction_helper.create_interaction(
            id=str(uuid.uuid4()),
            interaction_summary=interaction_summary,
            user_id=st.session_state.user_id,
        )

    def get_interaction_pairs(self):
        """Gets the interactions for the current user in 'UUID:STR' format"""
        interactions = None

        interactions = self.interaction_helper.get_interactions_by_user_id(
            st.session_state.user_id
        )

        if not interactions:
            return None

        # Reverse the list so the most recent interactions are at the top
        interactions.reverse()

        interaction_pairs = [f"{i.id}:{i.interaction_summary}" for i in interactions]

        print(f"get_interaction_pairs: interaction_pairs: {str(interaction_pairs)}")

        return interaction_pairs

    def ensure_interaction(self):
        """Ensures that an interaction exists for the current user"""

        # Only do this if we haven't already done it
        if (
            "interaction_ensured" not in st.session_state
            or not st.session_state["interaction_ensured"]
        ):
            if not self.get_interaction_pairs():
                self.create_interaction("Empty Chat")

            st.session_state["interaction_ensured"] = True

    def load_interaction_selectbox(self):
        """Loads the interaction selectbox"""

        try:
            st.sidebar.selectbox(
                "Select Conversation",
                self.get_interaction_pairs(),
                key="interaction_summary_selectbox",
                format_func=lambda x: x.split(":")[1],
                on_change=self.load_ai,
            )
        except Exception as e:
            logging.error(f"Error loading interaction selectbox: {e}")

    def get_selected_interaction_id(self):
        """Gets the selected interaction id from the selectbox"""
        selected_interaction_pair = st.session_state.get(
            "interaction_summary_selectbox"
        )

        if not selected_interaction_pair:
            return None

        selected_interaction_id = selected_interaction_pair.split(":")[0]

        logging.info(
            f"get_selected_interaction_id: selected_interaction_id: {selected_interaction_id}"
        )

        return selected_interaction_id

    def load_ai(self):
        """Loads the AI instance for the selected interaction id"""
        selected_interaction_id = self.get_selected_interaction_id()

        if "ai" not in st.session_state:
            # First time loading the page
            logging.debug("load_ai: ai not in session state")
            ai_instance = RetrievalAugmentedGenerationAI(
                configuration=st.session_state["config"],
                interaction_id=selected_interaction_id,
                user_email=self.user_email,
                streaming=True,
            )
            st.session_state["ai"] = ai_instance

        elif selected_interaction_id and selected_interaction_id != str(
            st.session_state["ai"].interaction_manager.interaction_id
        ):
            # We have an AI instance, but we need to change the interaction id
            print(
                "load_ai: interaction id is not none and not equal to ai interaction id"
            )
            ai_instance = RetrievalAugmentedGenerationAI(
                configuration=st.session_state["config"],
                interaction_id=selected_interaction_id,
                user_email=self.user_email,
                streaming=True,
            )
            st.session_state["ai"] = ai_instance

    def setup_new_chat_button(self):
        with st.sidebar.container():
            if st.sidebar.button("New Chat", key="new_chat_button"):
                self.create_interaction("Empty Chat")
                st.experimental_rerun()

    def get_available_collections(self, interaction_id) -> dict[str, int]:
        collections = self.documents_helper.get_collections(interaction_id)

        # Create a dictionary of collection id to collection summary
        collections_dict = {
            collection.collection_name: collection.id for collection in collections
        }

        return collections_dict

    def collection_id_from_option(self, option, interaction_id):
        collections_dict = self.get_available_collections(interaction_id)

        if option in collections_dict:
            return collections_dict[option]
        else:
            return None

    def create_collection(self, name):
        selected_interaction_id = self.get_selected_interaction_id()

        print(f"Creating collection {name} (interaction id: {selected_interaction_id})")
        
        collection = self.documents_helper.create_collection(
            name,
            selected_interaction_id,
        )

        print(f"Created collection {collection.collection_name}")

        return collection.id

    def create_collections_container(self, main_window_container):
        # Note: The styleable container does not work on firefox yet
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

        selected_interaction_id = self.get_selected_interaction_id()

        with main_window_container:
            with stylable_container(key="collections_container", css_styles=css_style):
                if "ai" in st.session_state:
                    st.caption("Selected document collection:")
                    # This is a hack, but it works
                    col1, col2 = st.columns([0.80, 0.2])
                    col1.selectbox(
                        "Active document collection",
                        self.get_available_collections(selected_interaction_id),
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
                            self.create_collection(
                                st.session_state["new_collection_name"]
                            )
                            st.experimental_rerun()

                    if "ai" in st.session_state:
                        option = st.session_state["active_collection"]
                        if option:
                            collection_id = self.collection_id_from_option(
                                option, selected_interaction_id
                            )

                            st.session_state[
                                "ai"
                            ].interaction_manager.collection_id = collection_id

                            loaded_docs = st.session_state[
                                "ai"
                            ].interaction_manager.get_loaded_documents_for_display()

                            uploader = st.session_state.get('file_uploader', None)

                            with st.expander("File Ingestion Options", expanded=uploader != None and len(uploader) > 0):
                                st.toggle(
                                    "Upload files into same dir (important for code)",
                                    key="use_same_upload_dir",
                                    value=True,
                                )
                                st.toggle(
                                    "Overwrite existing files",
                                    key="overwrite_existing_files",
                                    value=True,
                                )
                                st.toggle("Split documents", key="split_documents", value=True)
                                st.text_input("Chunk size", key="file_chunk_size", value=500)
                                st.text_input("Chunk overlap", key="file_chunk_overlap", value=50)

                            with st.expander("RAG Options", expanded=False):
                                st.toggle("Show LLM thoughts", key="show_llm_thoughts", value=True)
                                st.text_input("Top K", key="search_top_k", value=10)

                            with st.expander(
                                label=f"({len(loaded_docs)}) documents in {option}",
                                expanded=False,
                            ):
                                for doc in loaded_docs:
                                    st.write(doc)
                        else:
                            st.warning("No collection selected")

    def select_documents(self):
        with st.sidebar.container():
            active_collection = st.session_state.get("active_collection")

            uploaded_files = st.file_uploader(
                "Choose your files",
                accept_multiple_files=True,
                disabled=(active_collection == None),
                key="file_uploader",
            )

            status = st.status(f"File status", expanded=False, state="complete")

            if uploaded_files and active_collection:
                collection_id = None

                if active_collection:
                    collection_id = self.collection_id_from_option(
                        active_collection,
                        st.session_state["ai"].interaction_manager.interaction_id,
                    )            

                if (
                    active_collection
                    and st.button("Ingest files")
                    and len(uploaded_files) > 0
                ):
                    self.ingest_files(
                        uploaded_files,
                        active_collection,
                        collection_id,
                        status,
                        st.session_state["overwrite_existing_files"],
                        st.session_state["split_documents"],
                        int(st.session_state.get("file_chunk_size", 500)),
                        int(st.session_state.get("file_chunk_overlap", 50)),
                    )

    def ingest_files(
        self,
        uploaded_files,
        active_collection,
        collection_id,
        status,
        overwrite_existing_files,
        split_documents,
        chunk_size,
        chunk_overlap,
    ):
        """Ingests the uploaded files into the specified collection"""
        if not active_collection:
            st.error("No collection selected")
            return

        if not uploaded_files:
            st.error("No files selected")
            return

        if not collection_id:
            st.error("No collection id found")
            return
        
        status.update(
            label=f"Ingesting files and adding to '{active_collection}'",
            state="running",
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    rag_ui = RagUI()

    # Always comes first!
    rag_ui.load_configuration()

    rag_ui.set_page_config()

    # Get the user from the environment variables
    user_email = os.environ.get("USER_EMAIL", None)

    if not user_email:
        raise ValueError("USER_EMAIL environment variable not set")

    if rag_ui.ensure_user(user_email):
        rag_ui.set_user_id_from_email(user_email)
        rag_ui.ensure_interaction()
        rag_ui.load_interaction_selectbox()
        # Set up columns for chat and collections
        col1, col2 = st.columns([0.65, 0.35])

        rag_ui.load_ai()
        rag_ui.setup_new_chat_button()
        rag_ui.create_collections_container(col2)

        rag_ui.select_documents()

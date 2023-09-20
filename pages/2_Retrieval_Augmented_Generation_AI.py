import streamlit as st
import logging
import os
import sys
import uuid

from src.configuration.assistant_configuration import RetrievalAugmentedGenerationConfigurationLoader

from src.ai.rag_ai import RetrievalAugmentedGenerationAI

from src.db.models.users import Users
from src.db.models.interactions import Interactions


class RagUI:
    def __init__(self):
        self.users_helper = Users()
        self.interaction_helper = Interactions()
    
    def load_configuration(self):
        """Loads the configuration from the path"""
        rag_config_path = os.environ.get(
            "RAG_CONFIG_PATH",
            "configurations/rag_configs/openai_rag.json",
        )

        if "config" not in st.session_state:
            st.session_state["config"] = RetrievalAugmentedGenerationConfigurationLoader.from_file(
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

        interactions = self.interaction_helper.get_interactions_by_user_id(st.session_state.user_id)

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

        print("loading ai")
        rag_ui.load_ai()


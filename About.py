# Import necessary modules with clear names
from src.db.database.creation_utilities import CreationUtilities
from src.db.models.vector_database import VectorDatabase
import src.ui.streamlit_shared as ui_shared
import streamlit as st

# Constants
PAGE_TITLE = "Hello"
PAGE_ICON = "😎"
ABOUT_JARVIS_HEADER = "# About Jarvis 🤖"

# Documentation strings and error messages
ERROR_MSG_ROLE_TYPES = "Error ensuring conversation role types: {}. You probably didn't run the `migration_utilities.create_migration()`"


def verify_database():
    """
    Verifies that the database is set up correctly by performing the following:
    - Enables the pgvector extension if not already enabled.
    - Runs migration scripts to set up the database schema.
    - Ensures that default conversation role types are populated in the database.
    """
    # Enable pgvector extension
    CreationUtilities.create_pgvector_extension()

    # Run migration scripts
    CreationUtilities.run_migration_scripts()

    # Populate default conversation role types
    try:
        VectorDatabase().ensure_conversation_role_types()
    except Exception as e:
        print(ERROR_MSG_ROLE_TYPES.format(e))


def setup_streamlit_interface():
    """
    Configures the Streamlit page and displays the UI components for the application.
    """
    # Set Streamlit page configuration
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON)

    # Display the header for the About section
    st.write(ABOUT_JARVIS_HEADER)

    # Display the version information from the shared UI module
    ui_shared.show_version()

    # Display the capabilities of Jarvis
    st.markdown(
        """
    Contains a general purpose AI that can do a lot of things.
    
    Capabilities:
    - ✅ Chat with the AI (Conversation Mode)
    - ✅ Get the News
    - ✅ Get the Weather
    - ✅ Upload your Documents, and talk about them with the AI, including:
        - ✅ Search for information
        - ✅ Summarize a topic or whole documents
        - ✅ Perform multi-hop queries, such as "What is the capital of the country that has the highest population in Europe?"
    - ✅ Code Understanding
        - ✅ Code Summarization
        - ✅ Code Review
        - ✅ Code Documentation
        - ✅ Unit Test Generation
    """
    )


# Main execution
if __name__ == "__main__":
    verify_database()
    setup_streamlit_interface()

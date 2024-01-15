# Import necessary modules with clear names
import sys
import traceback
from src.db.database.creation_utilities import CreationUtilities
from src.db.models.default_data import (
    ensure_conversation_role_types,
    ensure_supported_source_control_providers,
)
from src.db.models.vector_database import VectorDatabase
import src.ui.streamlit_shared as ui_shared
import streamlit as st

# Constants
PAGE_TITLE = "Hello"
PAGE_ICON = "😎"
ABOUT_JARVIS_HEADER = "# About Jarvis 🤖"

# Documentation strings and error messages
ERROR_MSG_ROLE_TYPES = "Error ensuring conversation role types are in the database: {}. You probably didn't run the `migration_utilities.create_migration()`"
ERROR_MSG_SOURCE_CONTROL = "Error ensuring supported source control providers are in the database: {}. You probably didn't run the `migration_utilities.create_migration()`"


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
        ensure_conversation_role_types()
    except Exception as e:
        print(ERROR_MSG_ROLE_TYPES.format(e))

    try:
        ensure_supported_source_control_providers()
    except Exception as e:
        print(ERROR_MSG_SOURCE_CONTROL.format(e))


def setup_streamlit_interface():
    """
    Configures the Streamlit page and displays the UI components for the application.
    """
    try:
        # Set Streamlit page configuration
        try:
            st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON)

            # Display the header for the About section
            st.write(ABOUT_JARVIS_HEADER)
        except:
            pass

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
    except:
        # This whole thing is dumb as shit, and I don't know why python is like this... maybe I'm just a noob.
        # Check to see if the type of exception is a "StopException",
        # which gets thrown when a user navigates away from a page while the debugger is attached.
        # But we don't have access to that type, so we have to check the string.  Dumb.

        # Get the last exception
        exc_type, exc_value, exc_traceback = sys.exc_info()

        if "StopException" in str(exc_value.__class__):
            # If so, then just return
            return
        else:
            # Otherwise, raise the exception
            raise


# Main execution
if __name__ == "__main__":
    verify_database()
    setup_streamlit_interface()

from src.db.database.creation_utilities import CreationUtilities
from src.db.models.vector_database import VectorDatabase
import src.ui.streamlit_shared as ui_shared

import streamlit as st


def verify_database():
    """Verifies that the database is set up correctly"""

    # Make sure the pgvector extension is enabled
    CreationUtilities.create_pgvector_extension()

    # Run the migrations (these should be a part of the docker container)
    CreationUtilities.run_migration_scripts()

    # Ensure any default or standard data is populated
    # Conversation role types
    try:
        VectorDatabase().ensure_conversation_role_types()
    except Exception as e:
        print(
            f"Error ensuring conversation role types: {e}.  You probably didn't run the `migration_utilities.create_migration()`"
        )

verify_database()

st.set_page_config(
    page_title="Hello",
    page_icon="😎",
)

st.write("# About Jarvis 🤖")

st.sidebar.success("Select an AI above.")

ui_shared.show_version()

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
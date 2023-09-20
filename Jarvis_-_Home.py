from src.db.database.creation_utilities import CreationUtilities
from src.db.models.vector_database import VectorDatabase

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

st.write("# Welcome to Jarvis! 🤖")

st.sidebar.success("Select an AI above.")

st.markdown(
    """
    ### General AI
    Contains a general AI that can do most anything.
    - ✅ Chat with the AI
    - ✅ Current Events
    - ✅ Weather    
    - ✅ Retrieval Augmented Generation (This will eventually be moved to the RAG AI)
    - ✅ Software Development (This will eventually be moved to the Software Development AI)

    Use this AI to chat with Jarvis, ask about the weather, or ask about current events.  
    You should also use this AI when loading your documents, such as Word, PDF, Excel, or other documents that you may want to chat with Jarvis about.

    ** Note: Currently the General AI is the only AI that can chat with your documents.  This will be moved to the RAG AI as soon as I get to it. **

    ### Retrieval Augmented Generation (RAG) AI
    Contains an AI that can chat with your documents.
    - [x] Load Documents (Word, PDF, Excel, etc.)
    - [x] Question answering / chat over documents
    - [x] Summarize documents
    - [x] Specific tools for various document types (e.g. Excel- Summarize a column, count rows, etc.)        

    ### Software Development AI
    Contains an AI that can help you with software development.
    - [x] Code Completion
    - [x] Code Generation
    - [x] Code Summarization
    - [x] Code Understanding
    - [x] Unit Testing
    - [x] Code Documentation
"""
)
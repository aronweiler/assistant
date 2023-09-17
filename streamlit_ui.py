import streamlit as st

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
    - [x] Chat
    - [x] Current Events
    - [x] Weather    
    - [x] Jokes
    - [x] Retrieval Augmented Generation (Chat with your documents!)

    Use this AI to chat with Jarvis, ask about the weather, or ask about current events.  
    You should also use this AI when loading your documents, such as Word, PDF, Excel, or other documents that you may want to chat with Jarvis about.

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
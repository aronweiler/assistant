import streamlit as st           

# Main execution
if __name__ == "__main__":
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
# Import necessary modules with clear names
import logging
import sys

import requests
import streamlit as st

# Constants
PAGE_TITLE = "Hello"
PAGE_ICON = "😎"
ABOUT_JARVIS_HEADER = "# About Jarvis 🤖"


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
        show_version()

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

        if "StopException" in str(
            exc_value.__class__
        ) or "StreamlitAPIException" in str(exc_value.__class__):
            # If so, then just return
            return
        else:
            # Otherwise, raise the exception
            raise

def show_version():
    # Read the version from the version file
    version = ""
    with open("version.txt", "r") as f:
        version = f.read().strip()

    # Try to get the main version from my github repo, and if it's different, show an update message
    try:
        response = requests.get(
            "https://raw.githubusercontent.com/aronweiler/assistant/main/version.txt"
        )
        if response.status_code == 200:
            latest_version = response.text.strip()
            if latest_version != version:
                st.sidebar.warning(
                    f"⚠️ You are running a version of Jarvis that is not the release version."
                )
                st.sidebar.markdown(
                    f"You are running **{version}**, and the release version is **{latest_version}**."
                )
                st.sidebar.markdown(
                    "[Update Instructions](https://github.com/aronweiler/assistant#updating-jarvis-docker)"
                )
                st.sidebar.markdown(
                    "[Release Notes](https://github.com/aronweiler/assistant/blob/main/release_notes.md)"
                )
            else:
                try:
                    st.sidebar.info(
                        f"Version: {version} [Release Notes](https://github.com/aronweiler/assistant/blob/main/release_notes.md)"
                    )
                except:
                    pass
        else:
            st.sidebar.info(
                f"Version: {version} [Release Notes](https://github.com/aronweiler/assistant/blob/main/release_notes.md)"
            )

    except Exception as e:
        logging.error(f"Error checking for latest version: {e}")
        st.sidebar.info(f"Version: {version}")            

# Main execution
if __name__ == "__main__":
    setup_streamlit_interface()

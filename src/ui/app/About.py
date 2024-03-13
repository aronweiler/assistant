# Import necessary modules with clear names
from datetime import datetime, timedelta
import logging
import os
import sys

from passlib.hash import pbkdf2_sha256 as hasher

import requests
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.shared.database.models.users import Users
import streamlit_shared as ui_shared
from utilities import (
    DEFAULT_COOKIE_EXPIRY,
    get_cookie_manager,
    is_user_authenticated,
    cookie_manager,
)

# Constants
ABOUT_JARVIS_HEADER = "# About Jarvis 🤖"


def setup_streamlit_interface():
    """
    Configures the Streamlit page and displays the UI components for the application.
    """

    try:
        # Set Streamlit page configuration
        try:
            st.set_page_config(
                page_title="Jarvis",
                page_icon="🤖",
                layout="centered",
                initial_sidebar_state="expanded",
                menu_items={
                    "About": "https://github.com/aronweiler/assistant",
                    "Report a bug": "https://github.com/aronweiler/assistant/issues",
                },
            )
            # Display the header for the About section
            st.write(ABOUT_JARVIS_HEADER)
        except:
            pass

        # Display the version information from the shared UI module
        ui_shared.show_version()

        if not is_user_authenticated():
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")

            if st.button("Login"):
                user = Users().get_user_by_email(email)

                if user and hasher.verify(password, user.password_hash):
                    # Create the session, store the cookie
                    session_id = Users().create_session(user.id)

                    cookie_manager.set(
                        cookie="session_id",
                        val=session_id,
                        expires_at=datetime.now()
                        + timedelta(days=DEFAULT_COOKIE_EXPIRY),
                    )

                    st.success("Login Successful")
                else:
                    st.error("Invalid email or password")

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

        # # Protecting another page
        # if 'authenticated' in st.session_state and st.session_state['authenticated']:
        #     st.write('Welcome to the protected page!')
        # else:
        #     st.write('Please login to see this page.')

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


# Main execution
if __name__ == "__main__":
    setup_streamlit_interface()

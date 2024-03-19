# Import necessary modules with clear names
from datetime import datetime, timedelta
import logging
import os
import sys
import time

from passlib.hash import pbkdf2_sha256 as hasher

import requests
import streamlit as st


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.ui.app.navigation import make_sidebar
from src.shared.database.models.users import Users
import streamlit_shared as ui_shared
from utilities import (
    DEFAULT_COOKIE_EXPIRY,
    get_cookie_manager,
    set_page_config,
)

# Constants
ABOUT_JARVIS_HEADER = "# About Jarvis 🤖"


def setup_streamlit_interface():
    """
    Configures the Streamlit page and displays the UI components for the application.
    """

    # try:
    try:
        set_page_config(page_name="About", layout="centered")
        # Display the header for the About section
        st.write(ABOUT_JARVIS_HEADER)
    except:
        pass

    make_sidebar()

    # Display the version information from the shared UI module
    ui_shared.show_version()

    if not st.session_state.get("authenticated", False):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            logging.info(f"Attempting login with email: {email}")
            user = Users().get_user_by_email(email)

            if user:
                logging.info(f"Found user: {user.name}")
                if hasher.verify(password, user.password_hash):
                    logging.info("Login successful, creating session...")
                    # Create the session, store the cookie
                    session_id = Users().create_session(user.id)

                    get_cookie_manager().set(
                        cookie="session_id",
                        val=session_id,
                        expires_at=datetime.now() + timedelta(days=DEFAULT_COOKIE_EXPIRY),
                        key="cookie_manager_set_" + str(time.time()),
                    )

                    st.success("Login Successful")
                else:
                    logging.warning("Invalid password")
                    st.error("Invalid email or password")
            else:
                logging.warning("Invalid email")
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

if __name__ == "__main__":
    setup_streamlit_interface()

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


def setup_streamlit_interface():
    """
    Configures the Streamlit page and displays the UI components for the application.
    """

    # try:
    try:
        set_page_config(page_name="About", layout="centered")
    except:
        pass

    make_sidebar()

    # Display the version information from the shared UI module
    # ui_shared.show_version()

    col1, col2 = st.columns([0.3, 0.7])

    col1.image(
        "src/ui/app/assets/zippy1-transparent.png",
        width=150,
        use_column_width=False,
    )
    # Title of the landing page

    col2.markdown("## Your Personal AI Assistant")

    st.write(
        """
    Welcome to the future of AI interaction, where your digital assistant isn't just smart—it's intuitive, versatile, and incredibly powerful."""
    )

    # Displaying the catchy summary
    st.markdown("### Digital Enlightenment at Your Fingertips")
    st.write(
        "With an unparalleled ability to digest and understand documents, source code, websites, and even your daily weather or Yelp reviews, this AI is your gateway to a more efficient, informed, and connected world.\n\nImagine having the power to query documents, navigate code repositories, and interact with the digital world in ways you've never thought possible—all at your fingertips."
    )

    st.markdown("### Transformative Insights for Work and Play")
    st.write(
        "Our assistant doesn't just process information; it comprehends, analyzes, and provides insights that can transform the way you work, learn, and play.\n\nReady to revolutionize your digital experience? Join our beta program today and step into the future with us."
    )

    if not st.session_state.get("authenticated", False):
        col1a, col2a = st.columns([1, 1])
        # Call to action for users to sign up for the beta
        with col1a.expander("Apply to Join Our Beta Program"):
            # beta_email = st.text_input("Email", key="beta_email")
            st.write(
                "Email me to join our beta program (until online sign-ups are complete)."
            )
            st.markdown(
                f'<a href="mailto:aronweiler@gmail.com?subject=I\'d like to join the beta program!" target="_self" style="font-size: 1.5em;">aronweiler@gmail.com</a>',
                unsafe_allow_html=True,
            )

        with col2a.expander("Already a member? Log in here:"):
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
                            expires_at=datetime.now()
                            + timedelta(days=DEFAULT_COOKIE_EXPIRY),
                            key="cookie_manager_set_" + str(time.time()),
                        )

                        st.success("Login Successful")
                    else:
                        logging.warning("Invalid password")
                        st.error("Invalid email or password")
                else:
                    logging.warning("Invalid email")
                    st.error("Invalid email or password")


if __name__ == "__main__":
    setup_streamlit_interface()

from datetime import datetime, timedelta
import logging
import time
import streamlit as st
import extra_streamlit_components as stx

from shared.database.models.users import Users

DEFAULT_COOKIE_EXPIRY = 3
SESSION_EXPIRY = 3


@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    return stx.CookieManager()


st.set_page_config(
    page_title="Jarvis", page_icon="🤖", layout="wide", initial_sidebar_state="expanded"
)

cookie_manager = get_cookie_manager()


def ensure_authenticated():
    if not is_user_authenticated():
        st.write("Please login to see this page.")
        st.page_link("About.py", label="Login", icon="🔐")
        st.stop()


def is_user_authenticated():
    # Get the authentication cookie

    session_id = cookie_manager.get(cookie="session_id")

    if session_id:
        # Check the session in the database
        user = Users().get_user_by_session_id(session_id)

        # Check if the session is still valid
        if (
            user
            and user.session_created + timedelta(days=SESSION_EXPIRY) > datetime.now()
        ):
            # Make sure their email is in the session
            st.session_state.user_email = user.email
            return True
        elif user:
            # Their session has expired, update the session in the database, and clear the cookie
            Users().update_user_session(user.id, None)
            cookie_manager.delete(cookie="session_id")

    return False

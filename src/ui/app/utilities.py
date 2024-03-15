from datetime import datetime, timedelta
import logging
import time
import streamlit as st
import extra_streamlit_components as stx

from src.shared.database.models.users import Users

DEFAULT_COOKIE_EXPIRY = 3
SESSION_EXPIRY = 3


@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    return stx.CookieManager()


cookie_manager = None


def ensure_authenticated():
    if not is_user_authenticated():
        st.markdown("# Uh oh! 🤔\nIt looks like you're not logged in.  Please <a href='/' target='_self'>log in here</a>.", unsafe_allow_html=True)         
        st.stop()


def is_user_authenticated():
    # Get the authentication cookie
    global cookie_manager
    cookie_manager = get_cookie_manager()

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
            st.session_state.user_id = user.id
            return True
        elif user:
            # Their session has expired, update the session in the database, and clear the cookie
            Users().update_user_session(user.id, None)
            cookie_manager.delete(cookie="session_id")

    return False


def calculate_progress(total_size, current_position):
    """
    Calculate progress as a percentage within the range of 0-100.
    """
    progress = (current_position / total_size) * 100
    return int(min(progress, 100))


def set_page_config(page_name, layout="wide", initial_sidebar_state="expanded"):
    """Sets the page configuration"""

    st.set_page_config(
        page_title=f"Jarvis - {page_name}",
        page_icon="🤖",
        layout=layout,
        initial_sidebar_state=initial_sidebar_state,
        menu_items={
            "About": "https://github.com/aronweiler/assistant",
            "Report a bug": "https://github.com/aronweiler/assistant/issues",
        },
    )

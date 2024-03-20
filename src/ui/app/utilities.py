from datetime import datetime, timedelta
import logging
import time
import streamlit as st
import extra_streamlit_components as stx

from src.shared.database.models.users import Users

DEFAULT_COOKIE_EXPIRY = 3
SESSION_EXPIRY = 3


def get_cookie_manager():
    if not st.session_state.get("cookie_manager"):
        logging.info("Creating a new cookie manager")
        st.session_state.cookie_manager = stx.CookieManager(
            key="cookie_manager_" + str(time.time())
        )

    return st.session_state.cookie_manager


# cookie_manager = None





def is_user_authenticated():
    session_id = get_cookie_manager().get(cookie="session_id")

    if session_id:
        logging.info(f"Session ID found: {session_id}")
        # Check the session in the database
        user = Users().get_user_by_session_id(session_id)

        # Check if the session is still valid
        if (
            user
            and user.session_created + timedelta(days=SESSION_EXPIRY) > datetime.now()
        ):
            # Make sure their email is in the session
            st.session_state.authenticated = True
            st.session_state.user_email = user.email
            st.session_state.user_id = user.id
            st.session_state.is_admin = user.is_admin

            return True
        elif user:
            logging.info(f"User '{user.email}' session has expired")
            # Their session has expired, update the session in the database, and clear the cookie
            # This will force them to login again, as we'll return false
            Users().update_user_session(user.id, None)
            get_cookie_manager().delete(
                cookie="session_id", key="cookie_manager_delete_" + str(time.time())
            )

    user_email = st.session_state.get("user_email", "N/A")
    logging.info(f"User '{user_email}' is not authenticated")
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
            "About": "jarvis.zipbot.ai",
            "Report a bug": "https://github.com/aronweiler/assistant/issues",
        },
    )

import logging
import streamlit as st
from streamlit.errors import UncaughtAppException
from time import sleep
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.source_util import get_pages

from src.ui.app.utilities import is_user_authenticated, logout


def get_current_page_name():
    ctx = get_script_run_ctx()
    if ctx is None:
        raise RuntimeError("Couldn't get script context")

    pages = get_pages("")

    return pages[ctx.page_script_hash]["page_name"]


def make_sidebar():
    logging.info(f"Current page: {get_current_page_name()}")

    if not is_user_authenticated():
        if get_current_page_name() != "About":
            # If anyone tries to access a page that requires authentication without being logged in,
            # redirect them to the login page
            st.switch_page("About.py")


    else:
        logging.info(f"User '{st.session_state.user_email}' is authenticated")

        with st.sidebar:
            try:
                st.page_link("About.py", label="About Jarvis", icon="❓")
                st.page_link("pages/jarvis.py", label="Conversations", icon="💬")
                st.page_link("pages/tasks.py", label="Task Status", icon="⏱️")

                if st.session_state.is_admin:
                    st.page_link(
                        "pages/user_management.py", label="User Management", icon="👤"
                    )

                st.page_link("pages/settings.py", label="Settings", icon="⚙️")

                st.write("")

                if st.button("Log out"):
                    logout()

                st.divider()

            except Exception as e:
                logging.error(f"Error making sidebar: {e}")
                st.stop()

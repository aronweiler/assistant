import logging
import time
import streamlit as st

from src.ui.app.utilities import get_cookie_manager


try:
    get_cookie_manager().delete(
        cookie="session_id", key="cookie_manager_delete_" + str(time.time())
    )
except Exception as e:
    logging.error(f"Error deleting session cookie: {e}")
    st.switch_page("About.py")

st.session_state.user_email = None
st.session_state.user_id = None
st.session_state.is_admin = False
st.session_state.authenticated = False
# st.info("Logged out successfully!")
time.sleep(2)
st.switch_page("About.py")  # Force the redirect from there

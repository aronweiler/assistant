import streamlit as st

def ensure_authenticated():
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:        
        st.write('Please login to see this page.')
        st.page_link("About.py", label="Login", icon="🔐")
        st.stop()
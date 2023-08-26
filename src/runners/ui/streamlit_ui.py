import logging
import uuid
import streamlit as st
import os
from dotenv import load_dotenv

# for testing
import sys
sys.path.append("/Repos/assistant/src")

from ai.router_ai import RouterAI
from runners.runner import Runner
from configuration.assistant_configuration import AssistantConfiguration

from db.database.models import Conversation, Interaction, User
from db.models.vector_database import VectorDatabase, SearchType
from db.models.conversations import Conversations
from db.models.interactions import Interactions

from langchain.callbacks import StreamlitCallbackHandler

from run import load_assistant_configuration_and_ai

USER_EMAIL = "aronweiler@gmail.com"

def get_configuration_path():
    os.environ["ASSISTANT_CONFIG_PATH"] = "configurations/ui_configs/ui_ai.json"
    
    return os.environ.get(
            "ASSISTANT_CONFIG_PATH",
            "configurations/ui_configs/ui_ai.json",
        ) 

def setup_page():
    # Set up our page
    st.set_page_config(
        page_title="Hey Jarvis...", page_icon="😎", layout="centered", initial_sidebar_state="expanded", 
    )    
    
    st.title("Hey Jarvis...")

    # Sidebar
    st.sidebar.title("Conversations")

def get_interactions():
    interactions_helper = Interactions(config.ai.db_env_location)

    with interactions_helper.session_context(interactions_helper.Session()) as session:
        interactions = interactions_helper.get_interactions(session, USER_EMAIL)

        # Create a dictionary of interaction id to interaction summary
        interactions_dict = {interaction.interaction_summary: interaction.id for interaction in interactions}

        return interactions_dict


def populate_sidebar(config: AssistantConfiguration):        
    new_chat_button_clicked = st.sidebar.button("New Chat")
    
    if new_chat_button_clicked:
        # Recreate the AI with no interaction id (it will create one)
        ai_instance = RouterAI(config.ai)
        st.session_state['ai'] = ai_instance
    else:
        interactions_dict = get_interactions()

        if 'ai' not in st.session_state:
            # Check to see if there are interactions, and select the top one
            if len(interactions_dict) > 0:
                default_interaction_id = list(interactions_dict.values())[-1]
                ai_instance = RouterAI(config.ai, default_interaction_id)
                st.session_state['ai'] = ai_instance
            else:
                # Create a new interaction, this might be the first run
                ai_instance = RouterAI(config.ai)
                st.session_state['ai'] = ai_instance

                # Refresh the interactions if we created anything
                interactions_dict = get_interactions()
        
        selected_interaction_id = st.session_state['ai'].interaction_id

        selected_interaction_summary = st.sidebar.radio("Select Conversation", list(interactions_dict.keys()), index=list(interactions_dict.values()).index(selected_interaction_id))
        selected_interaction_id = interactions_dict[selected_interaction_summary]
            
        print("Selected interaction: " + str(selected_interaction_id))
        # Recreate the AI with the selected interaction id
        ai_instance = RouterAI(config.ai, selected_interaction_id)
        st.session_state['ai'] = ai_instance
                    

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Load environment variables from the .env file
    load_dotenv("/Repos/assistant/.env")

    setup_page()
    
    # Load the config
    assistant_config_path = get_configuration_path()
    config = AssistantConfiguration.from_file(assistant_config_path)

    populate_sidebar(config)

    # Get the config and the AI instance
    if 'ai' not in st.session_state:        
        st.warning("No AI instance found in session state")
        st.stop()
    else:
        ai_instance = st.session_state['ai']

    # Add old messages
    for message in ai_instance.get_conversation():
        if message.type == "human":
            with st.chat_message("user"):
                st.markdown(message.content)
        else:
            with st.chat_message("assistant"):
                st.markdown(message.content)            

    #with st.form("chat_form"):            
    prompt = st.chat_input("Say something")

    # output_container = st.empty()
    # answer_container = output_container.chat_message("assistant", avatar="🦜")
    # st_callback = StreamlitCallbackHandler(answer_container)

    # React to user input
    if prompt := st.chat_input("What is up?"):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            st.markdown(ai_instance.query(prompt))

    
    
    

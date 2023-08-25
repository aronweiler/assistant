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

from langchain.callbacks import StreamlitCallbackHandler

from run import load_assistant_configuration_and_ai


class StreamlitUIRunner:  # Should be a Runner eventually   

    def run(self, ai:RouterAI):
        load_dotenv("/Repos/assistant/.env")

        st.title("Hey Jarvis...")          

        # Add old messages
        for message in ai.get_conversation():
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
                st.markdown(ai.query(prompt, 1))

    
if __name__ == "__main__":    
    logging.basicConfig(level=logging.DEBUG)

    if 'ai' not in st.session_state:
        os.environ["ASSISTANT_CONFIG_PATH"] = "configurations/console_configs/router_console_ai.json"
    
        assistant_config_path = os.environ.get(
                "ASSISTANT_CONFIG_PATH",
                "configurations/console_configs/router_console_ai.json",
            )

        config, ai_instance = load_assistant_configuration_and_ai(assistant_config_path)

        st.session_state['ai'] = ai_instance
    else:
        ai_instance = st.session_state['ai']

    runner = StreamlitUIRunner()
    runner.run(ai_instance)    
    
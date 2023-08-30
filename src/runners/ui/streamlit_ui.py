import logging
import uuid
import streamlit as st
import os
from dotenv import load_dotenv

from langchain.callbacks import StreamlitCallbackHandler

# for testing
import sys

sys.path.append("/Repos/assistant/src")

from ai.router_ai import RouterAI

from configuration.assistant_configuration import AssistantConfiguration

from db.database.models import Conversation, Interaction, User

from db.models.vector_database import VectorDatabase, SearchType
from db.models.conversations import Conversations
from db.models.interactions import Interactions
from db.models.documents import Documents

from documents.document_loader import load_and_split_documents

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
        page_title="Hey Jarvis...",
        page_icon="😎",
        layout="centered",
        initial_sidebar_state="expanded",
    )

    st.title("Hey Jarvis...")

    # Sidebar
    # st.sidebar.title("Conversations")


def get_interactions():
    interactions_helper = Interactions(st.session_state["config"].ai.db_env_location)

    with interactions_helper.session_context(interactions_helper.Session()) as session:
        interactions = interactions_helper.get_interactions(session, USER_EMAIL)

        # Reverse the list so the most recent interactions are at the top
        interactions.reverse()

        # Create a dictionary of interaction id to interaction summary
        interactions_dict = {
            interaction.interaction_summary: interaction.id
            for interaction in interactions
        }

        return interactions_dict

def conversation_selected():
    if 'conversation_selector' not in st.session_state:
        interaction_key = None
    else:
        interaction_key = st.session_state['conversation_selector']

    interactions_dict = get_interactions()

    if 'conversation_selector' in st.session_state:
        selected_interaction_id = interactions_dict[interaction_key]
    else:
        selected_interaction_id = None

    print(f"conversation_selected: {str(interaction_key)} ({selected_interaction_id}), interactions: {str(interactions_dict)}")

    if "ai" not in st.session_state:
        print("conversation_selected: ai not in session state")
        # First time loading the page
        # Check to see if there are interactions, and select the top one
        if len(interactions_dict) > 0:
            default_interaction_id = list(interactions_dict.values())[0]
            ai_instance = RouterAI(
                st.session_state["config"].ai, default_interaction_id
            )
            st.session_state["ai"] = ai_instance
        else:
            print("conversation_selected: no interactions found")
            # Create a new interaction, this might be the first run
            ai_instance = RouterAI(st.session_state["config"].ai)
            st.session_state["ai"] = ai_instance

            # Refresh the interactions if we created anything
            interactions_dict = get_interactions()
    elif selected_interaction_id is not None and selected_interaction_id != str(st.session_state["ai"].interaction_id):
        print("conversation_selected: interaction id is not none and not equal to ai interaction id")
        # We have an AI instance, but we need to change the interaction
        ai_instance = RouterAI(st.session_state["config"].ai, selected_interaction_id)
        st.session_state["ai"] = ai_instance
    elif selected_interaction_id is None:
        print("conversation_selected: interaction id is none")
        # We have an AI instance, but they clicked new chat
        ai_instance = RouterAI(st.session_state["config"].ai)
        st.session_state["ai"] = ai_instance


def select_conversation():
    with st.sidebar.container():
        with st.sidebar.expander(
            label="Conversations", expanded=True
        ) as conversations_expander:
            new_chat_button_clicked = st.sidebar.button("New Chat", key="new_chat", on_click=conversation_selected)

            if new_chat_button_clicked:
                # Recreate the AI with no interaction id (it will create one)
                ai_instance = RouterAI(st.session_state["config"].ai)
                st.session_state["ai"] = ai_instance
            else:
                interactions_dict = get_interactions()                

                if 'ai' not in st.session_state:
                    conversation_selected()

                selected_interaction_id = st.session_state["ai"].interaction_id

                st.sidebar.radio(
                    "Select Conversation",
                    list(interactions_dict.keys()),
                    # index=list(interactions_dict.values()).index(
                    #     selected_interaction_id
                    # ),
                    key="conversation_selector",
                    on_change=conversation_selected
                )

                


def select_documents():
    with st.sidebar.container():
        status = st.status(f"File status", expanded=False, state="complete")
        with st.sidebar.expander("Documents", expanded=st.session_state.get('docs_expanded', False)) as documents_expander:
            # Add the widgets for uploading documents after setting the target collection name from the list of available collections
            uploaded_files = st.file_uploader(
                "Choose your files", accept_multiple_files=True
            )

            if uploaded_files is not None:
                st.session_state['docs_expanded'] = True
                # TODO: generate the list of collections from the database
                option = st.selectbox(
                    "Which collection would you like to use?",
                    ("general", "work", "personal"),
                )

                if option:
                    if st.button("Ingest files") and len(uploaded_files) > 0:
                        with st.spinner("Loading..."):
                            status.update(
                                label=f"Ingesting files and adding to {option}",
                                expanded=True,
                                state="running",
                            )

                            # get a unique temporary directory to store the files
                            temp_dir = os.path.join("temp", str(uuid.uuid4()))

                            if not os.path.exists(temp_dir):
                                os.makedirs(temp_dir)

                            for uploaded_file in uploaded_files:
                                status.info(
                                    f"Processing filename: {uploaded_file.name}"
                                )

                                # save the file to the temp directory
                                file_path = os.path.join(temp_dir, uploaded_file.name)
                                with open(file_path, "wb") as f:
                                    f.write(uploaded_file.getbuffer())

                            # Ingest the files into the database
                            documents = load_and_split_documents(
                                temp_dir, True, 500, 50
                            )

                            documents_helper = Documents(
                                st.session_state["config"].ai.db_env_location
                            )

                            with documents_helper.session_context(
                                documents_helper.Session()
                            ) as session:
                                print(f"Getting collection {option} (interaction id: {st.session_state['ai'].interaction_id})")
                                collection = documents_helper.get_collection(
                                    session,
                                    option,
                                    st.session_state["ai"].interaction_id,
                                )
                                print(f"Got collection {collection}")

                                # Create a collection if one does not exist
                                if collection is None:
                                    print(f"Creating collection {option} (interaction id: {st.session_state['ai'].interaction_id})")
                                    collection = documents_helper.create_collection(
                                        session,
                                        option,
                                        st.session_state["ai"].interaction_id,
                                    )
                                    print(f"Created collection {collection}")

                                status.info(f"Loading {len(documents)} chunks")

                                for document in documents:
                                    documents_helper.store_document(
                                        session=session,
                                        collection_id=collection.id,
                                        user_id=st.session_state["ai"].default_user_id,
                                        document_text=document.page_content,
                                        document_name=document.metadata["filename"],
                                        additional_metadata=document.metadata
                                    )

                                status.info("Complete")

                                status.update(
                                    label=f"Ingestion of {document.metadata['filename']} complete!",
                                    state="complete",
                                    expanded=False,
                                )

                            status.success("Done!", icon="✅")
                            uploaded_files.clear()
                    else:
                        status.warning("No files selected")

        


def handle_chat():
    # Get the config and the AI instance
    if "ai" not in st.session_state:
        st.warning("No AI instance found in session state")
        st.stop()
    else:
        ai_instance: RouterAI = st.session_state["ai"]

    # Add old messages
    for message in ai_instance.get_conversation_messages():
        if message.type == "human":
            with st.chat_message("user"):
                st.markdown(message.content)
        else:
            with st.chat_message("assistant"):
                st.markdown(message.content)

    # with st.form("chat_form"):
    prompt = st.chat_input("Say something")

    # React to user input
    if prompt := st.chat_input("What is up?"):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            st.markdown(ai_instance.query(prompt, st.session_state.get("selected_collection_id", None)))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Load environment variables from the .env file
    load_dotenv("/Repos/assistant/.env")

    # Load the config
    assistant_config_path = get_configuration_path()

    # Populate the config if it's not already there
    if "config" not in st.session_state:
        st.session_state["config"] = AssistantConfiguration.from_file(
            assistant_config_path
        )

    print("setting up page")
    setup_page()

    print("selecting conversation")
    select_conversation()

    print("selecting documents")
    select_documents()

    print("handling chat")
    handle_chat()

import logging
import uuid
import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.grid import grid
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


def get_available_collections(interaction_id) -> dict[str, int]:
    documents_helper = Documents(st.session_state["config"].ai.db_env_location)

    with documents_helper.session_context(documents_helper.Session()) as session:
        collections = documents_helper.get_collections(session, interaction_id)

        # Create a dictionary of collection id to collection summary
        collections_dict = {
            collection.collection_name: collection.id for collection in collections
        }

        return collections_dict


def collection_id_from_option(option, interaction_id):
    collections_dict = get_available_collections(interaction_id)

    if option in collections_dict:
        return collections_dict[option]
    else:
        return None

def create_collection(name):
    print(f"Creating collection {name} (interaction id: {st.session_state['ai'].interaction_id})")
    documents_helper = Documents(st.session_state["config"].ai.db_env_location)
    with documents_helper.session_context(documents_helper.Session()) as session:
        collection = documents_helper.create_collection(
            session,
            name,
            st.session_state["ai"].interaction_id,
        )
        print(
            f"Created collection {collection.collection_name}"
        )
        collection_id = collection.id

    return collection_id

def create_collections_container(main_window_container):

    css_style = """{
  position: fixed;  /* Keeps the element fixed on the screen */
  top: 100px;        /* Adjust the top position as needed */
  right: 100px;      /* Adjust the right position as needed */
  width: 300px;     /* Adjust the width as needed */
  max-width: 100%;  /* Ensures the element width doesn't exceed area */
  z-index: 9999;    /* Ensures the element is on top of other content */
  max-height: 80vh;     /* Sets the maximum height to 90% of the viewport height */
  overflow: auto;     /* Adds a scrollbar when the content overflows */
  overflow-x: hidden;   /* Hides horizontal scrollbar */
}"""

    #collections_container = main_window_container.container()
    with stylable_container(key="collections_container", css_styles=css_style):
        if "ai" in st.session_state:            
            st.caption("Selected collection:")
            # This is a hack, but it works
            col1, col2 = st.columns([.80, .2])
            col1.selectbox(
                "Active document collection",
                get_available_collections(st.session_state["ai"].interaction_id),
                key="active_collection",
                label_visibility="collapsed",
            )
            
            with st.container():
                col1, col2 = st.columns(2)
                col1.text_input("Collection name", key="new_collection_name", label_visibility="collapsed")
                new_collection = col2.button("Create New", key="create_collection")
                
                if new_collection and st.session_state.get("new_collection_name"):
                    create_collection(st.session_state["new_collection_name"])
                    #select_collection(st.session_state["new_collection_name"])                    

            if "ai" in st.session_state:
                option = st.session_state["active_collection"]
                if option:
                    collection_id = collection_id_from_option(
                        option, st.session_state["ai"].interaction_id
                    )

                    st.session_state["ai"].collection_id = collection_id

                    loaded_docs = st.session_state["ai"].get_loaded_documents(collection_id)

                    expander = st.expander(label=f"({len(loaded_docs)}) documents in {option}", expanded=True)

                    for doc in loaded_docs:
                        expander.write(doc)
                else:
                    st.warning("No collection selected")


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
    interaction_key = st.session_state.get("conversation_selector")
    interactions_dict = get_interactions()
    selected_interaction_id = interactions_dict.get(interaction_key)

    print(f"conversation_selected: {str(interaction_key)} ({selected_interaction_id}), interactions: {str(interactions_dict)}")

    if "ai" not in st.session_state:
        print("conversation_selected: ai not in session state")
        # First time loading the page
        # Check to see if there are interactions, and select the top one
        if interactions_dict:
            default_interaction_id = [value for value in interactions_dict.values()][0]
            ai_instance = RouterAI(st.session_state["config"].ai, default_interaction_id)
            st.session_state["ai"] = ai_instance
        else:
            print("conversation_selected: no interactions found")
            # Create a new interaction, this might be the first run
            ai_instance = RouterAI(st.session_state["config"].ai)
            st.session_state["ai"] = ai_instance

            # Refresh the interactions if we created anything
            interactions_dict = get_interactions()
    elif selected_interaction_id and selected_interaction_id != str(st.session_state["ai"].interaction_id):
        print("conversation_selected: interaction id is not none and not equal to ai interaction id")
        # We have an AI instance, but we need to change the interaction
        ai_instance = RouterAI(st.session_state["config"].ai, selected_interaction_id)
        st.session_state["ai"] = ai_instance
    elif not selected_interaction_id:
        print("conversation_selected: interaction id is none")
        # We have an AI instance, but they clicked new chat
        ai_instance = RouterAI(st.session_state["config"].ai)
        st.session_state["ai"] = ai_instance


def select_conversation():
    with st.sidebar.container():
        with st.sidebar.expander(
            label="Conversations", expanded=True
        ):
            new_chat_button_clicked = st.sidebar.button(
                "New Chat", key="new_chat"
            )

            if new_chat_button_clicked:
                # Recreate the AI with no interaction id (it will create one)
                ai_instance = RouterAI(st.session_state["config"].ai)
                st.session_state["ai"] = ai_instance
                st.session_state["conversation_selector"] = None
            else:
                interactions_dict = get_interactions()

                if "conversation_selector" not in st.session_state:
                    st.session_state["conversation_selector"] = None

                st.sidebar.selectbox(
                    "Select Conversation",
                    list(interactions_dict.keys()),
                    key="conversation_selector",
                    on_change=conversation_selected,
                )


def select_documents():
    with st.sidebar.container():
        status = st.status(f"File status", expanded=False, state="complete")
        with st.sidebar.expander(
            "Documents", expanded=st.session_state.get("docs_expanded", False)
        ) as documents_expander:
            # Add the widgets for uploading documents after setting the target collection name from the list of available collections
            uploaded_files = st.file_uploader(
                "Choose your files", accept_multiple_files=True
            )

            if uploaded_files is not None:
                st.session_state["docs_expanded"] = True
                # TODO: generate the list of collections from the database

                option = None
                if st.session_state.get("active_collection", None) is not None:
                    option = st.session_state["active_collection"]
                    collection_id = collection_id_from_option(
                        option, st.session_state["ai"].interaction_id
                    )
                    print(f"Active collection: {option}")

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
                                collection_id = collection_id_from_option(
                                    option, st.session_state["ai"].interaction_id
                                )

                                status.info(f"Loading {len(documents)} chunks")

                                for document in documents:
                                    documents_helper.store_document(
                                        session=session,
                                        collection_id=collection_id,
                                        user_id=st.session_state["ai"].default_user_id,
                                        document_text=document.page_content,
                                        document_name=document.metadata["filename"],
                                        additional_metadata=document.metadata,
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


def handle_chat(main_window_container):    
    container = main_window_container.container()
    # Get the config and the AI instance
    if "ai" not in st.session_state:
        container.warning("No AI instance found in session state")
        st.stop()
    else:
        ai_instance: RouterAI = st.session_state["ai"]

    # Add old messages
    for message in ai_instance.get_conversation_messages():
        if message.type == "human":
            with container.chat_message("user"):
                container.markdown(message.content)
        else:
            with container.chat_message("assistant"):
                container.markdown(message.content)

    # with st.form("chat_form"):
    prompt = main_window_container.chat_input("Enter your message here")

    # React to user input
    if prompt: # := container.chat_input("Enter your message here"):
        # Display user message in chat message container
        with container.chat_message("user"):
            container.markdown(prompt)

        with container.chat_message("assistant"):
            container.markdown(ai_instance.query(prompt))


def show_collections():
    pass


def loaded_documents():
    pass
    # with st.sidebar.container():
    #     if "ai" in st.session_state:
    #         option = st.session_state["active_collection"]
    #         if option:
    #             collection_id = collection_id_from_option(
    #                 option, st.session_state["ai"].interaction_id
    #             )

    #             loaded_docs = st.session_state["ai"].get_loaded_documents(collection_id)

    #             expander = st.sidebar.expander(label=f"Loaded documents ({len(loaded_docs)})", expanded=True)

    #             for doc in loaded_docs:
    #                 expander.write(doc)
    #         else:
    #             expander.write("No collection selected")


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
    # Set up our page
    st.set_page_config(
        page_title="Hey Jarvis...",
        page_icon="😎",
        layout="centered",
        initial_sidebar_state="expanded",
    )

    st.title("Hey Jarvis...")

    main_window_container = st.container()
    create_collections_container(main_window_container)    

    print("selecting conversation")
    select_conversation()

    print("selecting documents")
    select_documents()

    print("showing loaded documents")
    loaded_documents()

    print("handling chat")
    handle_chat(main_window_container)    

    print("showing collections")
    show_collections()

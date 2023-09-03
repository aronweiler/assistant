import logging
import uuid
import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.grid import grid
import os
from dotenv import load_dotenv

# from langchain.callbacks import StreamlitCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler

# for testing
import sys

sys.path.append("/Repos/assistant/src")

from ai.request_router import RequestRouter

from configuration.assistant_configuration import (
    AssistantConfiguration,
    ConfigurationLoader,
)

from db.models.vector_database import VectorDatabase, SearchType
from db.models.conversations import Conversations, SearchType, ConversationModel
from db.models.interactions import Interactions
from db.models.documents import Documents
from db.models.users import Users
from db.models.domain.file_model import FileModel
from db.models.domain.document_model import DocumentModel

from documents.document_loader import load_and_split_documents

from runners.ui.streamlit_agent_callback import StreamlitAgentCallbackHandler

USER_EMAIL = "aronweiler@gmail.com"


class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.container.markdown(self.text)


def get_configuration_path():
    os.environ[
        "ASSISTANT_CONFIG_PATH"
    ] = "configurations/console_configs/console_ai.json"

    return os.environ.get(
        "ASSISTANT_CONFIG_PATH",
        "configurations/console_configs/console_ai.json",
    )


def get_available_collections(interaction_id) -> dict[str, int]:
    documents_helper = Documents(st.session_state["config"].db_env_location)

    collections = documents_helper.get_collections(interaction_id)

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
    selected_interaction_id = get_selected_interaction_id()

    print(f"Creating collection {name} (interaction id: {selected_interaction_id})")

    documents_helper = Documents(st.session_state["config"].db_env_location)
    collection = documents_helper.create_collection(
        name,
        selected_interaction_id,
    )

    print(f"Created collection {collection.collection_name}")

    return collection.id


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

    selected_interaction_id = get_selected_interaction_id()

    with main_window_container:
        with stylable_container(key="collections_container", css_styles=css_style):
            if "ai" in st.session_state:
                st.caption("Selected document collection:")
                # This is a hack, but it works
                col1, col2 = st.columns([0.80, 0.2])
                col1.selectbox(
                    "Active document collection",
                    get_available_collections(selected_interaction_id),
                    key="active_collection",
                    label_visibility="collapsed",
                )

                with st.container():
                    col1, col2 = st.columns(2)
                    col1.text_input(
                        "Collection name",
                        key="new_collection_name",
                        label_visibility="collapsed",
                    )
                    new_collection = col2.button("Create New", key="create_collection")

                    if st.session_state.get("new_collection_name") and new_collection:
                        create_collection(st.session_state["new_collection_name"])

                if "ai" in st.session_state:
                    option = st.session_state["active_collection"]
                    if option:
                        collection_id = collection_id_from_option(
                            option, selected_interaction_id
                        )

                        st.session_state[
                            "ai"
                        ].interaction_manager.collection_id = collection_id

                        loaded_docs = st.session_state[
                            "ai"
                        ].interaction_manager.get_loaded_documents_for_display()

                        with st.expander(
                            label=f"({len(loaded_docs)}) documents in {option}",
                            expanded=False,
                        ):
                            for doc in loaded_docs:
                                st.write(doc)
                        # col1, col2 = expander.columns(2)
                        # for doc in loaded_docs:
                        #     col1.write(doc)
                        #     col2.button("Delete", key=f"delete_{doc}")
                    else:
                        st.warning("No collection selected")


def get_interaction_pairs():
    """Gets the interactions for the current user in 'UUID:STR' format"""
    interactions_helper = Interactions(st.session_state["config"].db_env_location)

    with interactions_helper.session_context(interactions_helper.Session()) as session:
        interactions = interactions_helper.get_interactions_by_user_id(
            session, st.session_state["user_id"]
        )

        if not interactions:
            return None

        # Reverse the list so the most recent interactions are at the top
        interactions.reverse()

        interaction_pairs = [f"{i.id}:{i.interaction_summary}" for i in interactions]

        print(f"get_interaction_pairs: interaction_pairs: {str(interaction_pairs)}")

        return interaction_pairs


def load_interaction_selectbox():
    """Loads the interaction selectbox"""

    st.sidebar.selectbox(
        "Select Conversation",
        get_interaction_pairs(),
        key="interaction_summary_selectbox",
        format_func=lambda x: x.split(":")[1],
        on_change=load_ai,
    )


def get_selected_interaction_id():
    """Gets the selected interaction id from the selectbox"""
    selected_interaction_pair = st.session_state.get("interaction_summary_selectbox")

    if not selected_interaction_pair:
        return None

    selected_interaction_id = selected_interaction_pair.split(":")[0]

    print(
        f"get_selected_interaction_id: selected_interaction_id: {selected_interaction_id}"
    )

    return selected_interaction_id


def load_ai():
    """Loads the AI instance for the selected interaction id"""
    selected_interaction_id = get_selected_interaction_id()

    if "ai" not in st.session_state:
        # First time loading the page
        print("load_ai: ai not in session state")
        ai_instance = RequestRouter(
            st.session_state["config"], selected_interaction_id, streaming=True
        )
        st.session_state["ai"] = ai_instance

    elif selected_interaction_id and selected_interaction_id != str(
        st.session_state["ai"].interaction_manager.interaction_id
    ):
        # We have an AI instance, but we need to change the interaction id
        print("load_ai: interaction id is not none and not equal to ai interaction id")
        ai_instance = RequestRouter(
            st.session_state["config"], selected_interaction_id, streaming=True
        )
        st.session_state["ai"] = ai_instance


def select_conversation():
    with st.sidebar.container():
        new_chat_button_clicked = st.sidebar.button("New Chat", key="new_chat_button")

        if new_chat_button_clicked:
            create_interaction("Empty Chat")


def select_documents():
    with st.sidebar.container():
        st.toggle("Show LLM thoughts", key="show_llm_thoughts", value=True)
        status = st.status(f"File status", expanded=False, state="complete")

        with st.expander("Documents", expanded=False):
            uploaded_files = st.file_uploader(
                "Choose your files", accept_multiple_files=True
            )

            active_collection = st.session_state.get("active_collection")

            if uploaded_files and active_collection:
                # docs_expanded.expanded = True

                collection_id = None

                if active_collection:
                    collection_id = collection_id_from_option(
                        active_collection,
                        st.session_state["ai"].interaction_manager.interaction_id,
                    )
                    print(f"Active collection: {active_collection}")

                if (
                    active_collection
                    and st.button("Ingest files")
                    and len(uploaded_files) > 0
                ):
                    ingest_files(
                        uploaded_files, active_collection, collection_id, status
                    )


def ingest_files(uploaded_files, active_collection, collection_id, status):
    with st.spinner("Loading..."):
        status.update(
            label=f"Ingesting files and adding to {active_collection}",
            expanded=True,
            state="running",
        )

        temp_dir = os.path.join("temp", str(uuid.uuid4()))

        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        documents_helper = Documents(st.session_state["config"].db_env_location)
        for uploaded_file in uploaded_files:
            status.info(f"Processing filename: {uploaded_file.name}")

            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            file = documents_helper.create_file(
                FileModel(
                    collection_id,
                    user_id=st.session_state["user_id"],
                    file_name=uploaded_file.name,
                )
            )

            # TODO: Make this configurable
            documents = load_and_split_documents(file_path, True, 500, 50)

            status.info(f"Loading {len(documents)} chunks for {uploaded_file.name}")

            for document in documents:
                documents_helper.store_document(
                    DocumentModel(
                        collection_id=collection_id,
                        file_id=file.id,
                        user_id=st.session_state["user_id"],
                        document_text=document.page_content,
                        document_name=document.metadata["filename"],
                        additional_metadata=document.metadata,
                    )
                )

            # Use up to the first 10 document chunks to classify this document
            classify_string = f"Please attempt to classify this text, and provide any relevant summary that you can extract from this (probably partial) text.\n\nFile name: {uploaded_file.name}\n\n--- TEXT CHUNK ---\n"
            for d in documents[:10]:
                classify_string += f"{d.page_content}\n\n"

            classify_string += "\n\n--- END TEXT CHUNK ---\n\nSure! Here is the summary I extracted from the text:\n"

            ai_instance: RequestRouter = st.session_state["ai"]

            file.file_summary = ai_instance.llm.predict(classify_string)

            file.file_classification = ai_instance.llm.predict(
                f"Using the following short summary of a file, please classify it as one of the following:\n\nDocument\nCode\nSpreadsheet\nEmail\nUnknown\n\n{file.file_summary}\n\nSure! I classified this file as: "
            )

            print(
                f"File summary: {file.file_summary}, classification: {file.file_classification}"
            )

        status.info("Complete")
        status.update(
            label=f"Document ingestion complete!",
            state="complete",
            expanded=False,
        )

        status.success("Done!", icon="✅")
        uploaded_files.clear()


def refresh_messages_session_state(ai_instance):
    """Pulls the messages from the token buffer on the AI for the first time, and put them into the session state"""

    buffer_messages = (
        ai_instance.interaction_manager.conversation_token_buffer_memory.buffer_as_messages
    )

    print(f"Length of messages retrieved from AI: {str(len(buffer_messages))}")

    st.session_state["messages"] = []

    for message in buffer_messages:
        if message.type == "human":
            st.session_state["messages"].append(
                {"role": "user", "content": message.content, "avatar": "🗣️"}
            )
        else:
            st.session_state["messages"].append(
                {"role": "assistant", "content": message.content, "avatar": "🤖"}
            )

    # with st.chat_message("user", avatar="👤"):
    #             st.markdown(m.content)

    #  = ai_instance.interaction_manager.conversation_token_buffer_memory.buffer_as_messages

    # for (
    #     m
    # ) in (
    #     ai_instance.interaction_manager.postgres_chat_message_history.messages
    # ):


def show_old_messages(ai_instance):
    refresh_messages_session_state(ai_instance)

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"], avatar=message["avatar"]):
            st.markdown(message["content"])


# TODO: Replace the DB backed chat history with a cached one here!
def handle_chat(main_window_container):
    with main_window_container.container():
        # Get the AI instance from session state
        if "ai" not in st.session_state:
            st.warning("No AI instance found in session state")
            st.stop()
        else:
            ai_instance = st.session_state["ai"]

        show_old_messages(ai_instance)

    # Get user input (must be outside of the container)
    prompt = st.chat_input("Enter your message here", key="chat_input")

    if prompt:
        with main_window_container.container():
            st.chat_message("user", avatar="👤").markdown(prompt)

            with st.chat_message("assistant", avatar="🤖"):
                llm_callbacks = []
                llm_callbacks.append(StreamHandler(st.container().empty()))

                agent_callbacks = []
                if st.session_state["show_llm_thoughts"]:
                    print("showing agent thoughts")
                    agent_callback = StreamlitAgentCallbackHandler(
                        st.container(),
                        expand_new_thoughts=True,
                        collapse_completed_thoughts=True,
                    )
                    agent_callbacks.append(agent_callback)

                collection_id = collection_id_from_option(
                    st.session_state["active_collection"],
                    ai_instance.interaction_manager.interaction_id,
                )

                result = ai_instance.query(
                    prompt,
                    collection_id=collection_id,
                    llm_callbacks=llm_callbacks,
                    agent_callbacks=agent_callbacks,
                )

                print(f"Result: {result}")


def set_user_id_from_email(email):
    users_helper = Users(st.session_state["config"].db_env_location)
    with users_helper.session_context(users_helper.Session()) as session:
        user = users_helper.get_user_by_email(session, email)
        st.session_state["user_id"] = user.id


def create_interaction(interaction_summary):
    interactions_helper = Interactions(st.session_state["config"].db_env_location)

    interactions_helper.create_interaction(        
        id=str(uuid.uuid4()),
        interaction_summary=interaction_summary,
        user_id=st.session_state["user_id"]
    )


def ensure_interaction():
    """Ensures that an interaction exists for the current user"""

    # Only do this if we haven't already done it
    if (
        "interaction_ensured" not in st.session_state
        or not st.session_state["interaction_ensured"]
    ):
        if not get_interaction_pairs():
            create_interaction("Empty Chat")

        st.session_state["interaction_ensured"] = True


def load_configuration():
    # Load environment variables from the .env file
    load_dotenv("/Repos/assistant/.env")

    assistant_config_path = get_configuration_path()
    if "config" not in st.session_state:
        st.session_state["config"] = ConfigurationLoader.from_file(
            assistant_config_path
        )


def set_page_config():
    st.set_page_config(
        page_title="Jarvis",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Hey Jarvis 🤖...")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Always comes first!
    load_configuration()

    set_page_config()

    set_user_id_from_email(USER_EMAIL)

    ensure_interaction()

    load_interaction_selectbox()

    # Set up columns for chat and collections
    col1, col2 = st.columns([0.65, 0.35])

    print("loading ai")
    load_ai()

    print("selecting conversation")
    select_conversation()

    print("creating collections container")
    create_collections_container(col2)

    print("selecting documents")
    select_documents()

    print("handling chat")
    handle_chat(col1)

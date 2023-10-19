import logging
import os
import uuid

import streamlit as st
from streamlit.runtime.scriptrunner import RerunException

from src.db.models.users import Users
from src.db.models.documents import FileModel, DocumentModel, Documents
from src.db.models.interactions import Interactions
from src.db.models.conversations import Conversations
from langchain.callbacks.streamlit import StreamlitCallbackHandler
from src.ai.callbacks.streaming_only_callback import StreamingOnlyCallbackHandler

from src.utilities.hash_utilities import calculate_sha256

from src.documents.document_loader import load_and_split_documents
from streamlit_extras.stylable_container import stylable_container


def delete_conversation_item(id: int):
    """Deletes the conversation item with the specified id"""
    # Delete the conversation item. (Note: This just sets the is_deleted flag to True)
    conversations_helper = Conversations()
    conversations_helper.delete_conversation(id)


def set_confirm_conversation_item_delete(id: int, val: bool):
    st.session_state[f"confirm_conversation_item_delete_{id}"] = val


def scroll_to_bottom(control_name):
    javascript_code = """
<script>
    function scrollColumnToBottom() {{
    const columnElement = document.getElementById('{control_name}');
    const lastChild = columnElement.lastElementChild;
    lastChild.scrollIntoView();
    }}
</script>
""".format(
        control_name=control_name
    )

    st.markdown(javascript_code, unsafe_allow_html=True)
    st.markdown("<script>scrollColumnToBottom();</script>", unsafe_allow_html=True)


class IngestionSettings:
    def __init__(self):
        self.chunk_size = 500
        self.chunk_overlap = 50
        self.split_documents = True
        self.file_type = "Document"
        self.summarize_chunks = False
        self.summarize_document = False


def set_user_id_from_email(user_email):
    """Sets the user_id in the session state from the user's email"""
    users_helper = Users()

    user = users_helper.get_user_by_email(user_email)
    st.session_state.user_id = user.id


def load_conversation_selectbox(load_ai_callback, tab):
    """Loads the interaction selectbox"""

    try:
        tab.selectbox(
            "Select Conversation",
            get_interaction_pairs(),
            key="interaction_summary_selectbox",
            format_func=lambda x: x.split(":")[1],
            on_change=load_ai_callback,
        )

    except Exception as e:
        logging.error(f"Error loading interaction selectbox: {e}")


def set_confirm_interaction_delete(val):
    st.session_state.confirm_interaction_delete = val


def create_interaction(interaction_summary):
    """Creates an interaction for the current user with the specified summary"""
    Interactions().create_interaction(
        id=str(uuid.uuid4()),
        interaction_summary=interaction_summary,
        user_id=st.session_state.user_id,
    )


def get_interaction_pairs():
    """Gets the interactions for the current user in 'UUID:STR' format"""
    interactions = None

    interactions = Interactions().get_interactions_by_user_id(st.session_state.user_id)

    if not interactions:
        return None

    # Reverse the list so the most recent interactions are at the top
    interactions.reverse()

    interaction_pairs = [f"{i.id}:{i.interaction_summary}" for i in interactions]

    print(f"get_interaction_pairs: interaction_pairs: {str(interaction_pairs)}")

    return interaction_pairs


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


def ensure_user(user_email):
    users_helper = Users()

    user = users_helper.get_user_by_email(user_email)

    if not user:
        st.markdown(f"Welcome to Jarvis, {user_email}! Let's get you set up.")

        # Create the user by showing them a prompt to enter their name, location, age
        name = st.text_input("Enter your name")
        location = st.text_input("Enter your location")

        if name and location:  # Check if both name and location inputs are not empty
            if st.button("Create Your User!"):
                user = users_helper.create_user(
                    email=user_email, name=name, location=location, age=999
                )
            else:
                return False
        else:
            return False
    else:
        return True


def get_selected_interaction_id():
    """Gets the selected interaction id from the selectbox"""
    selected_interaction_pair = st.session_state.get("interaction_summary_selectbox")

    if not selected_interaction_pair:
        return None

    selected_interaction_id = selected_interaction_pair.split(":")[0]

    logging.info(
        f"get_selected_interaction_id: selected_interaction_id: {selected_interaction_id}"
    )

    return selected_interaction_id


def delete_interaction(interaction_id):
    """Deletes the conversation item with the specified id"""

    # Delete the interaction (Note: This just sets the is_deleted flag to True)
    interactions_helper = Interactions()
    interactions_helper.delete_interaction(interaction_id)

    # Mark the individual conversation items as deleted, as well
    conversations_helper = Conversations()
    conversations_helper.delete_conversation_by_interaction_id(interaction_id)

    set_confirm_interaction_delete(False)


def setup_new_chat_button(tab):
    with tab.container():
        col1, col2, col3 = tab.columns([0.5, 0.25, 0.25])
        if col1.button("New Chat", key="new_chat_button"):
            create_interaction("Empty Chat")
            try:
                st.rerun()
            except RerunException:
                pass

        if "confirm_interaction_delete" not in st.session_state:
            st.session_state.confirm_interaction_delete = False

        if st.session_state.confirm_interaction_delete == False:
            col2.button(
                "🗑️",
                help="Delete this conversation?",
                on_click=set_confirm_interaction_delete,
                kwargs={"val": True},
                key=str(uuid.uuid4()),
            )
        else:
            col2.button(
                "✅",
                help="Click to confirm delete",
                key=str(uuid.uuid4()),
                on_click=delete_interaction,
                kwargs={"interaction_id": get_selected_interaction_id()},
            )
            col3.button(
                "❌",
                help="Click to cancel delete",
                on_click=set_confirm_interaction_delete,
                kwargs={"val": False},
                key=str(uuid.uuid4()),
            )

        tab.divider()


def get_available_collections():
    collections = Documents().get_collections()

    # Create a dictionary of collection id to collection summary
    collections_list = [
        f"{collection.id}:{collection.collection_name}" for collection in collections
    ]

    collections_list.insert(0, "-1:---")

    return collections_list


def get_selected_collection_id():
    """Gets the selected collection id from the selectbox"""
    selected_collection_pair = st.session_state.get("active_collection")

    if not selected_collection_pair:
        return None

    selected_collection_id = selected_collection_pair.split(":")[0]

    logging.info(
        f"get_selected_collection_id(): selected_collection_id: {selected_collection_id}"
    )

    return selected_collection_id


def get_selected_collection_name():
    """Gets the selected collection name from the selectbox"""
    selected_collection_pair = st.session_state.get("active_collection")

    if not selected_collection_pair:
        return None

    selected_collection_name = selected_collection_pair.split(":")[1]

    return selected_collection_name


def create_collection():
    if st.session_state["new_collection_name"]:
        collection = Documents().create_collection(
            st.session_state["new_collection_name"]
        )

        logging.info(
            f"New collection created: {collection.id} - {collection.collection_name}"
        )

        if "rag_ai" in st.session_state:
            st.session_state.rag_ai.interaction_manager.collection_id = collection.id
            st.session_state.rag_ai.interaction_manager.interactions_helper.update_interaction_collection(
                get_selected_interaction_id(), collection.id
            )

        return collection.id


def set_ingestion_settings():
    if not st.session_state.ingestion_settings:
        st.session_state.ingestion_settings = IngestionSettings()

    file_type = st.session_state.get("file_type", 0)

    if "Spreadsheet" in file_type:
        st.session_state.ingestion_settings.chunk_size = 250
        st.session_state.ingestion_settings.chunk_overlap = 50
        st.session_state.ingestion_settings.split_documents = True
        st.session_state.ingestion_settings.file_type = "Spreadsheet"
        st.session_state.ingestion_settings.summarize_chunks = False
        st.session_state.ingestion_settings.summarize_document = False
    elif "Code" in file_type:
        st.session_state.ingestion_settings.chunk_size = 0
        st.session_state.ingestion_settings.chunk_overlap = 0
        st.session_state.ingestion_settings.split_documents = False
        st.session_state.ingestion_settings.file_type = "Code"
        st.session_state.ingestion_settings.summarize_chunks = True
        st.session_state.ingestion_settings.summarize_document = True
    else:  # Document
        st.session_state.ingestion_settings.chunk_size = 600
        st.session_state.ingestion_settings.chunk_overlap = 100
        st.session_state.ingestion_settings.split_documents = True
        st.session_state.ingestion_settings.file_type = "Document"
        st.session_state.ingestion_settings.summarize_chunks = False
        st.session_state.ingestion_settings.summarize_document = False


def select_documents(tab, ai=None):
    # Handle the first time
    if not "ingestion_settings" in st.session_state:
        st.session_state.ingestion_settings = IngestionSettings()

    with tab.container():
        active_collection_id = get_selected_collection_id()
        if not active_collection_id:
            st.error("No document collection selected")
            return

        with st.expander("Ingestion Settings", expanded=True):
            st.radio(
                "File type",
                [
                    "Document (Word, PDF, TXT)",
                    "Spreadsheet (XLS, CSV)",
                    "Code (Python, C++)",
                ],
                key="file_type",
                on_change=set_ingestion_settings,
            )

            st.markdown(
                "<small>*📝 Group uploaded documents together by **File type** for best results!*</small>",
                unsafe_allow_html=True,
            )

            st.toggle(
                "Overwrite existing files",
                key="overwrite_existing_files",
                value=False,
            )

            st.toggle(
                "Summarize Chunks",
                key="summarize_chunks",
                value=st.session_state.ingestion_settings.summarize_chunks,
            )

            st.toggle(
                "Summarize Document",
                help="⚠️ This is a longer running process!  Might cost significant 💰 and ⌛ depending on your files.",
                key="summarize_document",
                value=st.session_state.ingestion_settings.summarize_document,
            )

            st.toggle(
                "Split documents",
                key="split_documents",
                value=st.session_state.ingestion_settings.split_documents,
            )
            col1, col2 = st.columns(2)
            col1.text_input(
                "Chunk size",
                key="file_chunk_size",
                value=st.session_state.ingestion_settings.chunk_size,
            )
            col2.text_input(
                "Chunk overlap",
                key="file_chunk_overlap",
                value=st.session_state.ingestion_settings.chunk_overlap,
            )

        with tab.form(key="upload_files_form", clear_on_submit=True):
            uploaded_files = st.file_uploader(
                "Choose your files",
                accept_multiple_files=True,
                disabled=(active_collection_id == None),
                key="file_uploader",
            )

            submit_button = st.form_submit_button("Ingest files", type="primary")

            status = st.status(f"Ready to ingest", expanded=False, state="complete")

            if uploaded_files and active_collection_id:
                if active_collection_id:
                    if submit_button:
                        ingest_files(
                            uploaded_files,
                            active_collection_id,
                            status,
                            st.session_state.get("overwrite_existing_files", True),
                            st.session_state.get("split_documents", True),
                            st.session_state.get("summarize_chunks", False),
                            st.session_state.get("summarize_document", False),
                            int(st.session_state.get("file_chunk_size", 500)),
                            int(st.session_state.get("file_chunk_overlap", 50)),
                            ai,
                        )


def ingest_files(
    uploaded_files,
    active_collection_id,
    status,
    overwrite_existing_files,
    split_documents,
    summarize_chunks,
    summarize_document,
    chunk_size,
    chunk_overlap,
    ai=None,
):
    """Ingests the uploaded files into the specified collection"""

    documents_helper = Documents()

    if not active_collection_id:
        st.error("No collection selected")
        return

    if not uploaded_files:
        st.error("No files selected")
        return

    status.update(
        label=f"Ingesting files and adding to '{get_selected_collection_name()}'",
        state="running",
    )

    # First upload the files to our temp directory
    uploaded_file_paths, root_temp_dir = upload_files(uploaded_files, status)

    with status.container():
        with st.empty():
            st.info(f"Processing {len(uploaded_file_paths)} files...")
            logging.info(f"Processing {len(uploaded_file_paths)} files...")
            # First see if there are any files we can't load
            files = []
            for uploaded_file_path in uploaded_file_paths:
                # Get the file name
                file_name = (
                    uploaded_file_path.replace(root_temp_dir, "").strip("/").strip("\\")
                )

                st.info(f"Verifying {uploaded_file_path}...")
                logging.info(f"Verifying {uploaded_file_path}...")

                # See if it exists in this collection
                existing_file = documents_helper.get_file_by_name(
                    file_name, active_collection_id
                )

                if existing_file and not overwrite_existing_files:
                    st.warning(
                        f"File '{file_name}' already exists, and overwrite is not enabled"
                    )
                    logging.warning(
                        f"File '{file_name}' already exists, and overwrite is not enabled"
                    )
                    logging.debug(f"Deleting temp file: {uploaded_file_path}")
                    os.remove(uploaded_file_path)
                    # status.update(
                    #     label=f"File '{file_name}' already exists, and overwrite is not enabled",
                    #     state="error",
                    # )

                    continue

                if existing_file and overwrite_existing_files:
                    # Delete the document chunks
                    documents_helper.delete_document_chunks_by_file_id(existing_file.id)

                    # Delete the existing file
                    documents_helper.delete_file(existing_file.id)

                # Read the file
                with open(uploaded_file_path, "rb") as file:
                    file_data = file.read()

                # Create the file
                logging.info(f"Creating file '{file_name}'...")
                files.append(
                    documents_helper.create_file(
                        FileModel(
                            user_id=st.session_state.user_id,
                            collection_id=active_collection_id,
                            file_name=file_name,
                            file_hash=calculate_sha256(uploaded_file_path),
                            file_data=file_data,
                            file_classification=st.session_state.ingestion_settings.file_type,
                        )
                    )
                )

            if not files or len(files) == 0:
                st.warning("Nothing to split... bye!")
                logging.warning("No files to ingest")
                return

            st.info("Splitting documents...")
            logging.info("Splitting documents...")

            is_code = st.session_state.ingestion_settings.file_type == "Code"

            # Pass the root temp dir to the ingestion function
            documents = load_and_split_documents(
                document_directory=root_temp_dir,
                split_documents=split_documents,
                is_code=is_code,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            st.info(f"Saving {len(documents)} document chunks...")
            logging.info(f"Saving {len(documents)} document chunks...")

            # For each document, create the file if it doesn't exist and then the document chunks
            for document in documents:
                # Get the file name without the root_temp_dir (preserving any subdirectories)
                file_name = (
                    document.metadata["filename"].replace(root_temp_dir, "").strip("/")
                )

                # Get the file reference
                file = next((f for f in files if f.file_name == file_name), None)

                if not file:
                    st.error(
                        f"Could not find file '{file_name}' in the database after uploading"
                    )
                    logging.error(
                        f"Could not find file '{file_name}' in the database after uploading"
                    )
                    break

                summary = ""
                if summarize_chunks and hasattr(
                    ai, "generate_detailed_document_chunk_summary"
                ):
                    logging.info("Summarizing chunk...")
                    summary = ai.generate_detailed_document_chunk_summary(
                        document_text=document.page_content
                    )

                # Create the document chunks
                logging.info(f"Inserting document chunk for file '{file_name}'...")
                documents_helper.store_document(
                    DocumentModel(
                        collection_id=active_collection_id,
                        file_id=file.id,
                        user_id=st.session_state.user_id,
                        document_text=document.page_content,
                        document_text_summary=summary,
                        document_text_has_summary=summary != "",
                        additional_metadata=document.metadata,
                        document_name=document.metadata["filename"],
                    )
                )

            summary = ""
            if summarize_document and hasattr(ai, "generate_detailed_document_summary"):
                for file in files:
                    # Note: this generates a summary and also puts it into the DB
                    ai.generate_detailed_document_summary(file_id=file.id)

                    logging.info(f"Created a summary of file: '{file.file_name}'")

            st.success(
                f"Successfully ingested {len(documents)} document chunks from {len(files)} files"
            )
            logging.info(
                f"Successfully ingested {len(documents)} document chunks from {len(files)} files"
            )
            status.update(
                label=f"✅ Ingestion complete",
                state="complete",
            )


def upload_files(uploaded_files, status):
    root_temp_dir = "temp/" + str(uuid.uuid4())

    # First upload all of the files- this needs to be done before we process them, in case there are inter-dependencies
    uploaded_file_paths = []
    with status.empty():
        for uploaded_file in uploaded_files:
            st.info(f"Uploading file: {uploaded_file.name}")

            file_path = os.path.join(root_temp_dir, uploaded_file.name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            uploaded_file_paths.append(file_path)

        st.success(f"Uploaded {len(uploaded_file_paths)} files")

    return uploaded_file_paths, root_temp_dir


def show_version():
    # Read the version from the version file
    version = ""
    with open("version.txt", "r") as f:
        version = f.read()

    st.sidebar.info(f"Version: {version}")


def on_change_collection():
    # Set the last active collection for this interaction (conversation)
    collection_id = get_selected_collection_id()
    interactions_helper = Interactions()
    interactions_helper.update_interaction_collection(
        get_selected_interaction_id(), collection_id
    )


def create_collection_selectbox(ai):
    col1, col2 = st.columns([0.80, 0.2])

    st.caption("Selected document collection:")

    available_collections = get_available_collections()
    selected_collection_id_index = 0
    # Find the index of the selected collection
    for i, collection in enumerate(available_collections):
        if int(collection.split(":")[0]) == int(
            ai.interaction_manager.get_interaction().last_selected_collection_id
        ):
            selected_collection_id_index = i
            break

    col1.selectbox(
        label="Active document collection",
        index=int(selected_collection_id_index),
        options=available_collections,
        key="active_collection",
        placeholder="Select a collection",
        label_visibility="collapsed",
        format_func=lambda x: x.split(":")[1],
        on_change=on_change_collection,
    )

    col2.button("➕", key="show_create_collection")


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
                {
                    "role": "user",
                    "content": message.content,
                    "avatar": "🗣️",
                    "id": message.additional_kwargs["id"],
                }
            )
        else:
            st.session_state["messages"].append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "avatar": "🤖",
                    "id": message.additional_kwargs["id"],
                }
            )


def show_old_messages(ai_instance):
    refresh_messages_session_state(ai_instance)

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"], avatar=message["avatar"]):
            col1, col2, col3 = st.columns([0.98, 0.1, 0.1])

            if (
                f"confirm_conversation_item_delete_{message['id']}"
                not in st.session_state
            ):
                st.session_state[
                    f"confirm_conversation_item_delete_{message['id']}"
                ] = False

            if (
                st.session_state[f"confirm_conversation_item_delete_{message['id']}"]
                == False
            ):
                col3.button(
                    "🗑️",
                    help="Delete this conversation entry?",
                    on_click=set_confirm_conversation_item_delete,
                    kwargs={"val": True, "id": message["id"]},
                    key=str(uuid.uuid4()),
                )
            else:
                col2.button(
                    "✅",
                    help="Click to confirm delete",
                    key=str(uuid.uuid4()),
                    on_click=delete_conversation_item,
                    kwargs={"id": message["id"]},
                )

                col3.button(
                    "❌",
                    help="Click to cancel delete",
                    on_click=set_confirm_conversation_item_delete,
                    kwargs={"val": False, "id": message["id"]},
                    key=str(uuid.uuid4()),
                )

            col1.markdown(message["content"])


def handle_chat(main_window_container, ai_instance):
    with main_window_container.container():
        # Get the AI instance from session state
        if not ai_instance:
            st.warning("No AI instance")
            st.stop()

        show_old_messages(ai_instance)

        st.write("")
        st.write("")
        st.write("")
        st.write("")
        st.write("")

    # Get user input (must be outside of the container)
    prompt = st.chat_input("Enter your message here", key="chat_input")

    # Write some css out to make the list of tools appear below the chat input
    css_style = """{
    position: fixed;
    bottom: 10px;
    right: 80px; 
    z-index: 9999;
    max-width: none;
}
"""

    with stylable_container(key="enabled_tools_container", css_styles=css_style):
        col1, col2, col3 = st.columns([0.06, 0.15, 0.7])

        col1.markdown(
            f'<div align="left"><b>AI Mode:</b></div>', unsafe_allow_html=True
        )

        def set_mode():
            mode = st.session_state["mode"]
            ai_instance.set_mode(mode)

        col2.selectbox(
            label="Mode",
            label_visibility="collapsed",
            options=["Auto", "Conversation Only"],
            key="mode",
            help="Select the mode to use. 'Auto' will automatically switch between 'Conversation Only' and 'Tool Using AI' based on the user's input.",
            on_change=set_mode,
        )

    if prompt:
        logging.debug(f"User input: {prompt}")

        with main_window_container.container():
            st.chat_message("user", avatar="👤").markdown(prompt)

            with st.chat_message("assistant", avatar="🤖"):
                thought_container = st.container()
                llm_container = st.container().empty()
                llm_callback = StreamingOnlyCallbackHandler(llm_container)
                agent_callbacks = []
                llm_callbacks = []
                # callbacks.append(results_callback)
                agent_callbacks.append(
                    StreamlitCallbackHandler(
                        parent_container=thought_container,
                        expand_new_thoughts=True,
                        collapse_completed_thoughts=True,
                    )
                )
                llm_callbacks.append(llm_callback)

                collection_id = get_selected_collection_id()

                logging.debug(f"Collection ID: {collection_id}")

                kwargs = {
                    "search_top_k": int(st.session_state["search_top_k"])
                    if "search_top_k" in st.session_state
                    else 5,
                    "search_method": st.session_state["search_method"]
                    if "search_method" in st.session_state
                    else "Similarity",
                    "use_pandas": st.session_state["use_pandas"]
                    if "use_pandas" in st.session_state
                    else True,
                    "override_file": st.session_state["override_file"].split(":")[0]
                    if "override_file" in st.session_state
                    and st.session_state["override_file"].split(":")[0] != "0"
                    else None,
                    "agent_timeout": int(st.session_state["agent_timeout"])
                    if "agent_timeout" in st.session_state
                    else 300,
                    "summarization_strategy": st.session_state["summarization_strategy"]
                    if "summarization_strategy" in st.session_state
                    else "map_reduce",
                    "re_run_user_query": st.session_state["re_run_user_query"]
                    if "re_run_user_query" in st.session_state
                    else True,
                }
                logging.debug(f"kwargs: {kwargs}")

                try:
                    result = ai_instance.query(
                        query=prompt,
                        collection_id=collection_id if collection_id != -1 else None,
                        agent_callbacks=agent_callbacks,
                        llm_callbacks=llm_callbacks,
                        kwargs=kwargs,
                    )
                except Exception as e:
                    logging.error(f"Error querying AI: {e}")
                    result = "Error querying AI, please try again (and see the logs)."

                logging.debug(f"Result: {result}")

                llm_container.markdown(result)

                # TODO: Put this thought container text into the DB (it provides great context!)
                # logging.debug(
                #     f"TODO: Put this thought container text into the DB (it provides great context!): {results_callback.response}"
                # )

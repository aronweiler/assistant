import logging
import os
from typing import List
import uuid
import asyncio

import streamlit as st
from streamlit.delta_generator import DeltaGenerator
import requests
from src.db.database.tables import UserSetting
from src.db.models.domain.user_settings_model import UserSettingModel
from src.db.models.user_settings import UserSettings


import src.ui.code_tab as code_tab
import src.ui.document_tab as document_tab

from src.configuration.assistant_configuration import (
    ApplicationConfigurationLoader,
)


from src.ai.rag_ai import RetrievalAugmentedGenerationAI

from src.utilities.configuration_utilities import (
    get_app_configuration,
    get_app_config_path,
)

from src.db.models.users import Users
from src.db.models.documents import FileModel, DocumentModel, Documents
from src.db.models.conversations import Conversations
from src.db.models.conversation_messages import ConversationMessages
from langchain.callbacks.streamlit import StreamlitCallbackHandler
from src.ai.callbacks.streaming_only_callback import (
    StreamlitStreamingOnlyCallbackHandler,
)

from src.utilities.hash_utilities import calculate_sha256

from src.documents.document_loader import DocumentLoader
from streamlit_extras.stylable_container import stylable_container

IMAGE_TYPES = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"]


def get_available_models():
    available_models_path = os.environ.get(
        "AVAILABLE_MODELS",
        "configurations/available_models.json",
    )

    return ApplicationConfigurationLoader.from_file(available_models_path)


def delete_conversation_item(id: int):
    """Deletes the conversation item with the specified id"""
    # Delete the conversation item. (Note: This just sets the is_deleted flag to True)
    conversation_messages_helper = ConversationMessages()
    conversation_messages_helper.delete_conversation(id)


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
        self.create_chunk_questions = False
        self.summarize_chunks = False
        self.summarize_document = False


def set_user_id_from_email(user_email):
    """Sets the user_id in the session state from the user's email"""
    if "user_id" in st.session_state:
        return

    users_helper = Users()

    user = users_helper.get_user_by_email(user_email)
    st.session_state.user_id = user.id


def get_conversation_id_index(conversation_pairs, selected_conversation):
    """Gets the index of the selected conversation id"""
    index = 0
    for i, conversation_pair in enumerate(conversation_pairs):
        if conversation_pair.split(":")[0] == selected_conversation:
            index = i
            break

    return index


def load_conversation_selectbox(load_ai_callback, tab: DeltaGenerator):
    """Loads the conversation selectbox"""
    with tab:
        try:
            conversation_pairs = get_conversation_pairs()
            if conversation_pairs is None:
                return

            index = 0
            if "rag_ai" in st.session_state:
                selected_conversation = st.session_state[
                    "rag_ai"
                ].conversation_manager.conversation_id
                index = get_conversation_id_index(
                    conversation_pairs, selected_conversation
                )

            st.selectbox(
                "Select Conversation",
                conversation_pairs,
                index=index,
                key="conversation_summary_selectbox",
                format_func=lambda x: x.split(":")[1],
                on_change=load_ai_callback,
            )

            col1, col2, col3, col4 = st.columns([0.15, 0.35, 0.15, 0.25])

            col3.button(
                "➕",
                help="Create a new conversation",
                key="new_chat_button",
                on_click=create_conversation,
                kwargs={
                    "conversation_summary": "Empty Chat",
                    "load_ai_callback": load_ai_callback,
                },
            )

            # col3
            if col4.button(
                "✏️",
                key="edit_conversation",
                help="Edit this conversation name",
                use_container_width=False,
            ):
                selected_conversation_pair = st.session_state.get(
                    "conversation_summary_selectbox"
                )

                with tab.form(key="edit_conversation_name_form", clear_on_submit=True):
                    # col1a, col2a = tab.columns(2)
                    st.text_input(
                        "Edit conversation name",
                        key="new_conversation_name",
                        value=selected_conversation_pair.split(":")[1],
                    )

                    st.form_submit_button(
                        label="Save",
                        # key="save_conversation_name",
                        help="Click to save",
                        type="primary",
                        on_click=update_conversation_name,
                    )

            if "confirm_conversation_delete" not in st.session_state:
                st.session_state.confirm_conversation_delete = False

            if st.session_state.confirm_conversation_delete == False:
                col1.button(
                    "🗑️",
                    help="Delete this conversation",
                    on_click=set_confirm_conversation_delete,
                    kwargs={"val": True},
                    key=str(uuid.uuid4()),
                )
            else:
                col2.button(
                    "✅",
                    help="Click to confirm delete",
                    key=str(uuid.uuid4()),
                    on_click=delete_conversation,
                    kwargs={"conversation_id": get_selected_conversation_id()},
                )
                col1.button(
                    "❌",
                    help="Click to cancel delete",
                    on_click=set_confirm_conversation_delete,
                    kwargs={"val": False},
                    key=str(uuid.uuid4()),
                )

        except Exception as e:
            logging.error(f"Error loading conversation selectbox: {e}")

        st.divider()


def set_confirm_conversation_delete(val):
    st.session_state.confirm_conversation_delete = val


def create_conversation(conversation_summary, load_ai_callback=None):
    """Creates an conversation for the current user with the specified summary"""

    if "user_id" not in st.session_state:
        # Sometimes this will happen if we're switching controls/screens
        return

    new_conversation = str(uuid.uuid4())

    Conversations().create_conversation(
        id=new_conversation,
        conversation_summary=conversation_summary,
        user_id=st.session_state.user_id,
    )

    if load_ai_callback:
        load_ai_callback(override_conversation_id=new_conversation)


def get_conversation_pairs():
    """Gets the interactions for the current user in 'UUID:STR' format"""
    interactions = None

    if "user_id" in st.session_state:
        interactions = Conversations().get_conversation_by_user_id(
            st.session_state.user_id
        )

    if not interactions:
        return None

    # Reverse the list so the most recent interactions are at the top
    interactions.reverse()

    conversation_pairs = [f"{i.id}:{i.conversation_summary}" for i in interactions]

    print(f"get_conversation_pairs: conversation_pairs: {str(conversation_pairs)}")

    return conversation_pairs


def ensure_conversation():
    """Ensures that an conversation exists for the current user"""

    # Only do this if we haven't already done it
    if (
        "conversation_ensured" not in st.session_state
        or not st.session_state["conversation_ensured"]
    ):
        if not get_conversation_pairs():
            create_conversation("Empty Chat")

        st.session_state["conversation_ensured"] = True


def ensure_user(user_email):
    users_helper = Users()

    user = users_helper.get_user_by_email(user_email)

    if not user:
        st.markdown(f"Welcome to Jarvis, {user_email}! Let's get you set up.")

        # Create the user by showing them a prompt to enter their name, location, age
        name = st.text_input("Enter your name")
        location = st.text_input("Enter your location")

        if name and location:  # Check if both name and location inputs are not empty
            # Display a confirmation button for the user to create their account
            if st.button("Create User", type="primary"):
                user = users_helper.create_user(
                    email=user_email, name=name, location=location, age=999
                )
                st.rerun()
            else:
                return False
        else:
            return False
    else:
        return True


def get_selected_conversation_id():
    """Gets the selected conversation id from the selectbox"""
    selected_conversation_pair = st.session_state.get("conversation_summary_selectbox")

    if not selected_conversation_pair:
        return None

    selected_conversation_id = selected_conversation_pair.split(":")[0]

    logging.info(
        f"get_selected_conversation_id: selected_conversation_id: {selected_conversation_id}"
    )

    return selected_conversation_id


def delete_conversation(conversation_id):
    """Deletes the conversation item with the specified id"""

    # Delete the conversation (Note: This just sets the is_deleted flag to True)
    interactions_helper = Conversations()
    interactions_helper.delete_conversation(conversation_id)

    # Mark the individual conversation items as deleted, as well
    conversation_messages_helper = ConversationMessages()
    conversation_messages_helper.delete_conversation_by_conversation_id(conversation_id)

    set_confirm_conversation_delete(False)


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


def get_selected_code_repo_id():
    """Gets the selected code repo id from the selectbox"""
    selected_code_repo_pair = st.session_state.get("active_code_repo")

    if not selected_code_repo_pair:
        return None

    selected_code_repo_id = selected_code_repo_pair.split(":")[0]

    logging.info(
        f"get_selected_code_repo_id(): selected_code_repo_id: {selected_code_repo_id}"
    )

    return selected_code_repo_id


def get_selected_embedding_name():
    collection_id = get_selected_collection_id()

    if collection_id == -1:
        return None

    collection = Documents().get_collection(collection_id)

    if not collection:
        return None

    return collection.embedding_name


def get_selected_collection_embedding_model_name():
    embedding_name = get_selected_embedding_name()

    if not embedding_name:
        return None

    key = get_app_configuration()["jarvis_ai"]["embedding_models"]["available"][
        embedding_name
    ]

    return key


def get_selected_collection_configuration():
    key = get_selected_collection_embedding_model_name()

    if not key:
        return None

    return get_app_configuration()["jarvis_ai"]["embedding_models"][key]


def get_selected_collection_name():
    """Gets the selected collection name from the selectbox"""
    selected_collection_pair = st.session_state.get("active_collection")

    if not selected_collection_pair:
        return None

    selected_collection_name = selected_collection_pair.split(":")[1]

    return selected_collection_name


def set_ingestion_settings():
    if not st.session_state.ingestion_settings:
        st.session_state.ingestion_settings = IngestionSettings()

    file_type = st.session_state.get("file_type", 0)

    if "Spreadsheet" in file_type:
        st.session_state.ingestion_settings.chunk_size = 250
        st.session_state.ingestion_settings.chunk_overlap = 50
        st.session_state.ingestion_settings.split_documents = True
        st.session_state.ingestion_settings.file_type = "Spreadsheet"
        st.session_state.ingestion_settings.create_chunk_questions = False
        st.session_state.ingestion_settings.summarize_chunks = False
        st.session_state.ingestion_settings.summarize_document = False
    elif "Code" in file_type:
        st.session_state.ingestion_settings.chunk_size = 0
        st.session_state.ingestion_settings.chunk_overlap = 0
        st.session_state.ingestion_settings.split_documents = False
        st.session_state.ingestion_settings.file_type = "Code"
        st.session_state.ingestion_settings.create_chunk_questions = False
        st.session_state.ingestion_settings.summarize_chunks = True
        st.session_state.ingestion_settings.summarize_document = True
    else:  # Document
        st.session_state.ingestion_settings.chunk_size = 450
        st.session_state.ingestion_settings.chunk_overlap = 50
        st.session_state.ingestion_settings.split_documents = True
        st.session_state.ingestion_settings.file_type = "Document"
        st.session_state.ingestion_settings.create_chunk_questions = True
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
                "Create Chunk Questions",
                help="This will create hypothetical questions for each chunk of text in the document, which will GREATLY aid in later retrievals.",
                key="create_chunk_questions",
                value=st.session_state.ingestion_settings.create_chunk_questions,
            )

            st.toggle(
                "Summarize Chunks",
                key="summarize_chunks",
                help="Summarize each document chunk.  This will aid in later retrievals, and document summaries.",
                value=st.session_state.ingestion_settings.summarize_chunks,
            )

            st.toggle(
                "Summarize Document",
                help="⚠️ This is a longer running process!  Might cost significant 💰 and ⌛ depending on your files.",
                key="summarize_document",
                value=st.session_state.ingestion_settings.summarize_document,
            )

            st.toggle(
                "Split documents by tokens",
                help="Documents will be split by tokens into chunks of text, which will be stored in the database- this setting determines how large those chunks are.\n\nWhen this is off, documents will be split by page.",
                key="split_documents",
                value=st.session_state.ingestion_settings.split_documents,
            )

            collection_config = get_selected_collection_configuration()
            if collection_config:
                max_chunk_size = collection_config["max_token_length"]
            else:
                max_chunk_size = 500

            col1, col2 = st.columns(2)
            col1.number_input(
                "Chunk size",
                key="file_chunk_size",
                min_value=0,
                step=1,
                max_value=max_chunk_size,
                value=st.session_state.ingestion_settings.chunk_size,
            )

            col2.number_input(
                "Chunk overlap",
                key="file_chunk_overlap",
                min_value=0,
                step=1,
                max_value=max_chunk_size - st.session_state.file_chunk_size,
                value=(
                    st.session_state.ingestion_settings.chunk_overlap
                    if st.session_state.ingestion_settings.chunk_overlap
                    <= max_chunk_size - st.session_state.file_chunk_size
                    else max_chunk_size - st.session_state.file_chunk_size
                ),
            )

            st.markdown(
                f"*Embedding model: **{get_selected_embedding_name()}**, max chunk size: **{max_chunk_size}***"
            )

        with tab.form(key="upload_files_form", clear_on_submit=True):
            uploaded_files = st.file_uploader(
                "Choose your files",
                accept_multiple_files=True,
                disabled=(active_collection_id == None),
                key="file_uploader",
            )

            submit_button = st.form_submit_button(
                "Ingest files",
                type="primary",
                disabled=(active_collection_id == None or active_collection_id == "-1"),
            )

            st.markdown(
                "*⚠️ Currently there is no async/queued file ingestion. Do not navigate away from this page, or click on anything else, while the files are being ingested.*"
            )

            status = st.status(f"Ready to ingest", expanded=False, state="complete")

            if uploaded_files and active_collection_id:
                if active_collection_id:
                    if submit_button:
                        ingest_files(
                            uploaded_files=uploaded_files,
                            active_collection_id=active_collection_id,
                            status=status,
                            overwrite_existing_files=st.session_state.get(
                                "overwrite_existing_files", True
                            ),
                            split_documents=st.session_state.get(
                                "split_documents", True
                            ),
                            create_chunk_questions=st.session_state.get(
                                "create_chunk_questions", False
                            ),
                            summarize_chunks=st.session_state.get(
                                "summarize_chunks", False
                            ),
                            summarize_document=st.session_state.get(
                                "summarize_document", False
                            ),
                            chunk_size=int(
                                st.session_state.get("file_chunk_size", 500)
                            ),
                            chunk_overlap=int(
                                st.session_state.get("file_chunk_overlap", 50)
                            ),
                            ai=ai,
                        )


def ingest_files(
    uploaded_files,
    active_collection_id,
    status,
    overwrite_existing_files,
    split_documents,
    create_chunk_questions,
    summarize_chunks,
    summarize_document,
    chunk_size,
    chunk_overlap,
    ai=None,
):
    """Ingests the uploaded files into the specified collection"""

    documents_helper = Documents()
    document_loader = DocumentLoader()
    documents = None

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

    ingest_progress_bar = st.progress(text="Uploading files...", value=0)

    # First upload the files to our temp directory
    uploaded_file_paths, root_temp_dir = upload_files(
        uploaded_files, status, ingest_progress_bar
    )

    with status.container():
        with st.empty():
            st.info(f"Processing {len(uploaded_file_paths)} files...")
            logging.info(f"Processing {len(uploaded_file_paths)} files...")
            # First see if there are any files we can't load
            files = []
            for uploaded_file_path in uploaded_file_paths:
                ingest_progress_bar.progress(
                    calculate_progress(
                        len(uploaded_file_paths),
                        uploaded_file_paths.index(uploaded_file_path) + 1,
                    ),
                    text=f"Uploading file {uploaded_file_paths.index(uploaded_file_path) + 1} of {len(uploaded_file_paths)}",
                )

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
                    # See if the hash on this file matches the one we have stored
                    if existing_file.file_hash == calculate_sha256(uploaded_file_path):
                        # It matches, so split the file using the existing document chunks settings
                        st.info(
                            f"File '{file_name}' already exists, and the hash matches, so we're checking to see if it's a RESUME op..."
                        )
                        logging.info(
                            f"File '{file_name}' already exists, and the hash matches, so we're checking to see if it's a RESUME op..."
                        )

                        if (
                            existing_file.file_classification
                            != st.session_state.ingestion_settings.file_type
                        ):
                            st.error(
                                f"File '{file_name}' already exists, and the hash matches, but the file type has changed.  Please set the overwrite option and try again."
                            )
                            logging.error(
                                f"File '{file_name}' already exists, and the hash matches, but the file type has changed.  Please set the overwrite option and try again."
                            )

                        # TODO: Fix all of this- it's a total inefficient mess, the document ingestion needs to be completely re-written

                        # Split the document
                        documents = asyncio.run(
                            document_loader.load_and_split_documents(
                                document_directory=root_temp_dir,
                                split_documents=split_documents,
                                is_code=existing_file.file_classification == "Code",
                                chunk_size=existing_file.chunk_size,
                                chunk_overlap=existing_file.chunk_overlap,
                            )
                        )

                        # Get the documents that match this file name
                        matching_documents = [
                            d
                            for d in documents
                            if d.metadata["filename"]
                            .replace(root_temp_dir, "")
                            .strip("/")
                            == file_name
                        ]

                        if (
                            len(matching_documents) == existing_file.document_count
                            or existing_file.document_count == 0
                        ):
                            files.append(existing_file)
                        else:
                            st.error(
                                f"File '{file_name}' already exists, and the hash matches, but the number of documents in the file has changed.  Please delete the file and try again."
                            )
                            logging.error(
                                f"File '{file_name}' already exists, and the hash matches, but the number of documents in the file has changed.  Please delete the file and try again."
                            )

                    st.warning(
                        f"File '{file_name}' already exists, and overwrite is not enabled"
                    )
                    logging.warning(
                        f"File '{file_name}' already exists, and overwrite is not enabled"
                    )
                    logging.debug(f"Deleting temp file: {uploaded_file_path}")
                    os.remove(uploaded_file_path)

                    continue

                elif not existing_file or (existing_file and overwrite_existing_files):
                    # Delete the document chunks
                    if existing_file:
                        documents_helper.delete_document_chunks_by_file_id(
                            existing_file.id
                        )

                        # Delete the existing file
                        documents_helper.delete_file(existing_file.id)

                    # File does not exist (or was deleted)
                    # Read the file
                    with open(uploaded_file_path, "rb") as file:
                        file_data = file.read()

                    # Start off with the default file classification
                    file_classification = st.session_state.ingestion_settings.file_type

                    # Override the classification if necessary
                    # Get the file extension
                    file_extension = os.path.splitext(file_name)[1]
                    # Check to see if it's an image
                    if file_extension in IMAGE_TYPES:
                        # It's an image, reclassify it
                        file_classification = "Image"

                    # Create the file
                    logging.info(f"Creating file '{file_name}'...")
                    file_model = documents_helper.create_file(
                        FileModel(
                            user_id=st.session_state.user_id,
                            collection_id=active_collection_id,
                            file_name=file_name,
                            file_hash=calculate_sha256(uploaded_file_path),
                            file_classification=file_classification,
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                        ),
                        file_data,
                    )
                    files.append(file_model)

            if not files or len(files) == 0:
                st.warning("Nothing to split... bye!")
                logging.warning("No files to ingest")
                ingest_progress_bar.empty()
                status.update(
                    label=f"⚠️ Ingestion complete (with warnings)",
                    state="complete",
                )
                return

            st.info("Splitting documents...")
            logging.info("Splitting documents...")

            is_code = st.session_state.ingestion_settings.file_type == "Code"

            # Pass the root temp dir to the ingestion function
            # if we've already split the docs, don't do it again
            if not documents:
                documents = asyncio.run(
                    document_loader.load_and_split_documents(
                        document_directory=root_temp_dir,
                        split_documents=split_documents,
                        is_code=is_code,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                    )
                )

            if documents == None:
                st.warning(
                    f"No documents could be extracted from these files.  Possible images detected..."
                )
                st.success(f"Completed ingesting {len(files)} files")
                status.update(
                    label=f"✅ Ingestion complete",
                    state="complete",
                )
                logging.info(
                    f"No documents could be extracted from these files.  Possible images detected..."
                )
                return

            save_split_documents(
                active_collection_id,
                status,
                create_chunk_questions,
                summarize_chunks,
                summarize_document,
                ai,
                documents_helper,
                ingest_progress_bar,
                root_temp_dir,
                files,
                documents,
            )

    # Done!
    st.balloons()


def save_split_documents(
    active_collection_id,
    status,
    create_chunk_questions,
    summarize_chunks,
    summarize_document,
    ai,
    documents_helper,
    ingest_progress_bar,
    root_temp_dir,
    files: List[FileModel],
    documents,
):
    document_chunk_length = len(documents)
    st.info(f"Saving {document_chunk_length} document chunks...")
    logging.info(f"Saving {document_chunk_length} document chunks...")

    # Update the document counts on the files- this will help if we have to resume
    file_to_chunk_count = {}
    for file in files:
        if file.document_count == 0:
            # Get the count of documents matching the file name
            document_count = len(
                [
                    d
                    for d in documents
                    if d.metadata["filename"].replace(root_temp_dir, "").strip("/")
                    == file.file_name
                ]
            )
            file.document_count = document_count
            documents_helper.update_document_count(file.id, document_count)

        # Get the number of documents already in the DB for this file
        current_document_count = documents_helper.get_document_chunk_count_by_file_id(
            file.id
        )

        file_to_chunk_count[file.file_name] = {
            "current_document_count": current_document_count,
            "total_document_count": file.document_count,
        }

    # Since this is all fucked up, and the documents are all in one list (multiple files in the same list)
    # I need to split this out into multiple lists, each associated with a single file
    file_documents = {}
    for document in documents:
        # Get the file name without the root_temp_dir (preserving any subdirectories)
        file_name = document.metadata["filename"].replace(root_temp_dir, "").strip("/")

        if file_name in file_documents:
            doc_list = file_documents[file_name]
        else:
            doc_list = []

        doc_list.append(document)
        file_documents[file_name] = doc_list

    # For each file, loop through the documents
    current_chunk = 0
    for file in files:
        logging.info(
            f"Processing {len(file_documents[file.file_name])} chunks for {file.file_name}"
        )

        if not file:
            st.error(
                f"Could not find file '{file_name}' in the database after uploading"
            )
            logging.error(
                f"Could not find file '{file_name}' in the database after uploading"
            )
            break

        current_document_count = file_to_chunk_count[file.file_name][
            "current_document_count"
        ]

        file_doc_chunk_len = len(file_documents[file.file_name])
        for index in range(current_document_count, file_doc_chunk_len):
            # TODO: Fix the progress bar
            ingest_progress_bar.progress(
                calculate_progress(file_doc_chunk_len, index + 1),
                text=f"Processing {file.file_name} chunk {index + 1} of {file_doc_chunk_len}",
            )

            document = file_documents[file.file_name][index]

            chunk_questions = None
            if create_chunk_questions and hasattr(ai, "generate_chunk_questions"):
                try:
                    logging.info("Creating questions for chunk...")
                    chunk_questions = ai.generate_chunk_questions(
                        text=document.page_content
                    )
                except Exception as e:
                    logging.error(f"Error creating questions for chunk: {e}")

            summary = ""
            if summarize_chunks and hasattr(
                ai, "generate_detailed_document_chunk_summary"
            ):
                logging.info("Summarizing chunk...")
                summary = ai.generate_detailed_document_chunk_summary(
                    chunk_text=document.page_content
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
                    embedding_model_name=get_selected_collection_embedding_model_name(),
                    question_1=(
                        chunk_questions.questions[0]
                        if chunk_questions and len(chunk_questions.questions) > 0
                        else ""
                    ),
                    question_2=(
                        chunk_questions.questions[1]
                        if chunk_questions and len(chunk_questions.questions) > 1
                        else ""
                    ),
                    question_3=(
                        chunk_questions.questions[2]
                        if chunk_questions and len(chunk_questions.questions) > 2
                        else ""
                    ),
                    question_4=(
                        chunk_questions.questions[3]
                        if chunk_questions and len(chunk_questions.questions) > 3
                        else ""
                    ),
                    question_5=(
                        chunk_questions.questions[4]
                        if chunk_questions and len(chunk_questions.questions) > 4
                        else ""
                    ),
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

    ingest_progress_bar.empty()


def calculate_progress(total_size, current_position):
    """
    Calculate progress as a percentage within the range of 0-100.
    """
    progress = (current_position / total_size) * 100
    return int(min(progress, 100))


def upload_files(uploaded_files, status, ingest_progress_bar):
    root_temp_dir = "temp/" + str(uuid.uuid4())

    # First upload all of the files- this needs to be done before we process them, in case there are inter-dependencies
    uploaded_file_paths = []
    with status.empty():
        for uploaded_file in uploaded_files:
            ingest_progress_bar.progress(
                calculate_progress(
                    len(uploaded_files), uploaded_files.index(uploaded_file) + 1
                ),
                text=f"Uploading file {uploaded_files.index(uploaded_file) + 1} of {len(uploaded_files)}",
            )
            st.info(f"Uploading file: {uploaded_file.name}")

            # Make sure there are no folder separators in the file name
            file_name = uploaded_file.name.replace("/", "-").replace("\\", "-")

            file_path = os.path.join(root_temp_dir, file_name)
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
        version = f.read().strip()

    # Try to get the main version from my github repo, and if it's different, show an update message
    try:
        response = requests.get(
            "https://raw.githubusercontent.com/aronweiler/assistant/main/version.txt"
        )
        if response.status_code == 200:
            latest_version = response.text.strip()
            if latest_version != version:
                st.sidebar.warning(
                    f"⚠️ You are running a version of Jarvis that is not the release version."
                )
                st.sidebar.markdown(
                    f"You are running **{version}**, and the release version is **{latest_version}**."
                )
                st.sidebar.markdown(
                    "[Update Instructions](https://github.com/aronweiler/assistant#updating-jarvis-docker)"
                )
                st.sidebar.markdown(
                    "[Release Notes](https://github.com/aronweiler/assistant/blob/main/release_notes.md)"
                )
            else:
                try:
                    st.sidebar.info(
                        f"Version: {version} [Release Notes](https://github.com/aronweiler/assistant/blob/main/release_notes.md)"
                    )
                except:
                    pass
        else:
            st.sidebar.info(
                f"Version: {version} [Release Notes](https://github.com/aronweiler/assistant/blob/main/release_notes.md)"
            )

    except Exception as e:
        logging.error(f"Error checking for latest version: {e}")
        st.sidebar.info(f"Version: {version}")


def create_documents_and_code_collections(ai):
    documents_tab, code = st.tabs(["Documents", "Code"])

    document_tab.create_documents_collection_tab(ai, documents_tab)
    code_tab.create_code_collection_tab(ai, code)


def refresh_messages_session_state(ai_instance):
    """Pulls the messages from the token buffer on the AI for the first time, and put them into the session state"""

    entire_chat_history = (
        ai_instance.conversation_manager.conversation_token_buffer_memory.chat_memory.messages
    )

    messages_in_memory = (
        ai_instance.conversation_manager.conversation_token_buffer_memory.buffer_as_messages
    )

    logging.info(
        f"Counts for --- `messages_in_memory`: {str(len(messages_in_memory))}, `entire_chat_history`: {str(len(entire_chat_history))}"
    )

    st.session_state["messages"] = []

    for message in entire_chat_history:
        if "messages" in st.session_state:  # Why streamlit, why???
            if message.type == "human":
                st.session_state["messages"].append(
                    {
                        "role": "user",
                        "content": message.content,
                        "avatar": "🗣️",
                        "id": message.additional_kwargs["id"],
                        "in_memory": message in messages_in_memory,
                    }
                )
            else:
                st.session_state["messages"].append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "avatar": "🤖",
                        "id": message.additional_kwargs["id"],
                        "in_memory": message in messages_in_memory,
                    }
                )


def show_old_messages(ai_instance):
    refresh_messages_session_state(ai_instance)

    if "messages" in st.session_state:
        for message in st.session_state["messages"]:
            with st.chat_message(message["role"], avatar=message["avatar"]):
                # TODO: Put better (faster) deleting of conversation items in place.. maybe checkboxes?

                if message["in_memory"]:
                    in_memory = "*🐘 :green[Message in chat memory]*"
                else:
                    in_memory = "*🙊 :red[Message not in chat memory]*"

                col1, col2, col3 = st.container().columns([0.10, 0.01, 0.01])

                col1.markdown(in_memory)

                st.markdown(message["content"])

                if (
                    f"confirm_conversation_item_delete_{message['id']}"
                    not in st.session_state
                ):
                    st.session_state[
                        f"confirm_conversation_item_delete_{message['id']}"
                    ] = False

                if (
                    st.session_state[
                        f"confirm_conversation_item_delete_{message['id']}"
                    ]
                    == False
                ):
                    col3.button(
                        "🗑️",
                        help="Delete this conversation entry",
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

    with stylable_container(
        key="additional_configuration_container", css_styles=css_style
    ):
        col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 1, 2, 1, 2])

        help_icon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'

        col1.markdown(
            f'<div align="right" title="Select the mode to use.\nAuto will automatically switch between a Conversation Only and Tool Using AI based on the users input.\nCode is a code-based AI specialist that will use the loaded repository.">{help_icon} <b>AI Mode:</b></div>',
            unsafe_allow_html=True,
        )

        ai_modes = ["Auto", "Conversation Only"]

        # Get the AI mode setting
        ai_mode = ai_instance.conversation_manager.get_user_setting(
            setting_name="ai_mode", default_value="Auto"
        ).setting_value

        col2.selectbox(
            label="Mode",
            label_visibility="collapsed",
            options=ai_modes,
            index=ai_modes.index(ai_mode),
            key="ai_mode",
            help="Select the mode to use.\nAuto will automatically switch between a Conversation Only and Tool Using AI based on the users input.\nCode is a code-based AI specialist that will use the loaded repository.",
            on_change=set_ai_mode,
        )

        if st.session_state.get("ai_mode", "auto").lower().startswith("auto"):
            col3.markdown(
                f'<div align="right" title="Turning this on will add an extra step to each request to the AI, where it will evaluate the tool usage and results, possibly triggering another planning stage.">{help_icon} <b>Evaluate Answer:</b></div>',
                unsafe_allow_html=True,
            )

            evaluate_response = UserSettings().get_user_setting(
                user_id=ai_instance.conversation_manager.user_id,
                setting_name="evaluate_response",
                default_value=False,
            )

            re_planning_threshold = UserSettings().get_user_setting(
                user_id=ai_instance.conversation_manager.user_id,
                setting_name="re_planning_threshold",
                default_value=0.5,
            )

            col4.toggle(
                label="Evaluate Response",
                label_visibility="collapsed",
                value=bool(evaluate_response.setting_value),
                key="evaluate_response",
                help="Turning this on will add an extra step to each request to the AI, where it will evaluate the tool usage and results, possibly triggering another planning stage.",
                on_change=save_user_setting,
                kwargs={
                    "setting_name": "evaluate_response",
                    "available_for_llm": evaluate_response.available_for_llm,
                },
            )

            col5.markdown(
                f'<div align="right" title="Threshold at which the AI will re-enter a planning stage.">{help_icon} <b>Re-Planning Threshold:</b></div>',
                unsafe_allow_html=True,
            )

            col6.slider(
                label="Re-Planning Threshold",
                label_visibility="collapsed",
                key="re_planning_threshold",
                min_value=0.0,
                max_value=1.0,
                value=float(re_planning_threshold.setting_value),
                step=0.1,
                help="Threshold at which the AI will re-enter a planning stage.",
                on_change=save_user_setting,
                kwargs={
                    "setting_name": "re_planning_threshold",
                    "available_for_llm": re_planning_threshold.available_for_llm,
                },
            )

        else:
            frequency_penalty = UserSettings().get_user_setting(
                user_id=ai_instance.conversation_manager.user_id,
                setting_name="frequency_penalty",
                default_value=0,
            )
            presence_penalty = UserSettings().get_user_setting(
                user_id=ai_instance.conversation_manager.user_id,
                setting_name="presence_penalty",
                default_value=0,
            )

            col3.markdown(
                f'<div align="right" title="Positive values will decrease the likelihood of the model repeating the same line verbatim by penalizing new tokens that have already been used frequently.">{help_icon} <b>Frequency Penalty:</b></div>',
                unsafe_allow_html=True,
            )

            col4.slider(
                label="Frequency Penalty",
                label_visibility="collapsed",
                key="frequency_penalty",
                min_value=-2.0,
                max_value=2.0,
                value=float(frequency_penalty.setting_value),
                step=0.1,
                help="The higher the penalty, the less likely the AI will repeat itself in the completion.",
                disabled=not st.session_state.get("ai_mode", "auto")
                .lower()
                .startswith("conversation"),
                on_change=save_user_setting,
                kwargs={
                    "setting_name": "frequency_penalty",
                    "available_for_llm": frequency_penalty.available_for_llm,
                },
            )

            col5.markdown(
                f'<div align="right" title="Positive values will increase the likelihood of the model talking about new topics by penalizing new tokens that have already been used.">{help_icon} <b>Presence Penalty:</b></div>',
                unsafe_allow_html=True,
            )

            col6.slider(
                label="Presence Penalty",
                label_visibility="collapsed",
                key="presence_penalty",
                min_value=-2.0,
                max_value=2.0,
                value=float(presence_penalty.setting_value),
                step=0.1,
                help="The higher the penalty, the more variety of words will be introduced in the completion.",
                disabled=not st.session_state.get("ai_mode", "auto")
                .lower()
                .startswith("conversation"),
                on_change=save_user_setting,
                kwargs={
                    "setting_name": "presence_penalty",
                    "available_for_llm": presence_penalty.available_for_llm,
                },
            )

    if prompt:
        logging.debug(f"User input: {prompt}")

        with main_window_container.container():
            st.chat_message("user", avatar="👤").markdown(prompt)

            with st.chat_message("assistant", avatar="🤖"):
                agent_callbacks = []
                llm_callbacks = []

                thought_container = st.container()
                llm_container = st.container().empty()

                show_llm_thoughts = (
                    UserSettings()
                    .get_user_setting(
                        user_id=ai_instance.conversation_manager.user_id,
                        setting_name="show_llm_thoughts",
                        default_value=False,
                    )
                    .setting_value
                )

                if show_llm_thoughts:
                    llm_callback = StreamlitStreamingOnlyCallbackHandler(llm_container)
                    agent_callback = StreamlitCallbackHandler(
                        parent_container=thought_container,
                        max_thought_containers=10,
                        expand_new_thoughts=True,
                        collapse_completed_thoughts=True,
                    )

                    agent_callbacks.append(agent_callback)
                    llm_callbacks.append(llm_callback)
                else:
                    # Show some kind of indicator that the AI is thinking
                    llm_container.info(icon="🤖", body="Thinking...")

                collection_id = get_selected_collection_id()

                logging.debug(f"Collection ID: {collection_id}")

                kwargs = {
                    "search_top_k": (
                        int(st.session_state["search_top_k"])
                        if "search_top_k" in st.session_state
                        else 5
                    ),
                    "search_type": (
                        st.session_state["search_type"]
                        if "search_type" in st.session_state
                        else "Similarity"
                    ),
                    "use_pandas": (
                        st.session_state["use_pandas"]
                        if "use_pandas" in st.session_state
                        else True
                    ),
                    "override_file": (
                        st.session_state["override_file"].split(":")[0]
                        if "override_file" in st.session_state
                        and st.session_state["override_file"].split(":")[0] != "0"
                        else None
                    ),
                    "agent_timeout": (
                        int(st.session_state["agent_timeout"])
                        if "agent_timeout" in st.session_state
                        else 300
                    ),
                    "max_iterations": (
                        int(st.session_state["max_iterations"])
                        if "max_iterations" in st.session_state
                        else 25
                    ),
                    "evaluate_response": (
                        st.session_state["evaluate_response"]
                        if "evaluate_response" in st.session_state
                        else False
                    ),
                    "re_planning_threshold": (
                        float(st.session_state["re_planning_threshold"])
                        if "re_planning_threshold" in st.session_state
                        else 0.5
                    ),
                }
                logging.debug(f"kwargs: {kwargs}")

                try:
                    ai_instance.conversation_manager.agent_callbacks = agent_callbacks
                    ai_instance.conversation_manager.llm_callbacks = llm_callbacks

                    result = ai_instance.query(
                        query=prompt,
                        collection_id=collection_id if collection_id != -1 else None,
                        kwargs=kwargs,
                    )
                except Exception as e:
                    logging.error(f"Error querying AI: {str(e)}")
                    result = f"An error occurred when attempting to fulfill your request.\n\n```console\n{str(e)}\n```"

                logging.debug(f"Result: {result}")

                llm_container.markdown(result)


def save_user_setting(setting_name, available_for_llm=False):
    user_id = st.session_state.user_id
    setting_value = st.session_state[setting_name]

    UserSettings().add_update_user_setting(
        user_id, setting_name, setting_value, available_for_llm
    )


def set_ai_mode():
    ai: RetrievalAugmentedGenerationAI = st.session_state["rag_ai"]
    ai.conversation_manager.set_user_setting(
        "ai_mode", st.session_state.get("ai_mode", "auto")
    )


def update_conversation_name():
    conversation_id = get_selected_conversation_id()
    conversation_name = st.session_state["new_conversation_name"]

    ai: RetrievalAugmentedGenerationAI = st.session_state["rag_ai"]
    ai.conversation_manager.conversations_helper.update_conversation_summary(
        conversation_id=conversation_id,
        conversation_summary=conversation_name,
        needs_summary=False,
    )

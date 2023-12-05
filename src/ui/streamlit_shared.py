import logging
import os
from threading import Timer
import time
import uuid

import streamlit as st
from streamlit.delta_generator import DeltaGenerator
import requests

from streamlit.runtime.scriptrunner import RerunException

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
from src.db.models.interactions import Interactions
from src.db.models.conversations import Conversations
from langchain.callbacks.streamlit import StreamlitCallbackHandler
from src.ai.callbacks.streaming_only_callback import StreamingOnlyCallbackHandler

from src.utilities.hash_utilities import calculate_sha256

from src.documents.document_loader import load_and_split_documents
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


def get_interaction_id_index(interaction_pairs, selected_interaction):
    """Gets the index of the selected interaction id"""
    index = 0
    for i, interaction_pair in enumerate(interaction_pairs):
        if interaction_pair.split(":")[0] == selected_interaction:
            index = i
            break

    return index

def load_conversation_selectbox(load_ai_callback, tab:DeltaGenerator):
    """Loads the interaction selectbox"""

    try:
        interaction_pairs = get_interaction_pairs()
        if interaction_pairs is None:
            return
        
        index = 0
        if "rag_ai" in st.session_state:
            selected_interaction = st.session_state["rag_ai"].interaction_manager.interaction_id        
            index = get_interaction_id_index(interaction_pairs, selected_interaction)            

        tab.selectbox(
            "Select Conversation",
            interaction_pairs,
            index=index,
            key="interaction_summary_selectbox",
            format_func=lambda x: x.split(":")[1],
            on_change=load_ai_callback,
        )

        col1, col2, col3, col4 = tab.columns([0.15, 0.35, 0.15, 0.25])

        col3.button(
            "➕",
            help="Create a new conversation",
            key="new_chat_button",
            on_click=create_interaction,
            kwargs={"interaction_summary": "Empty Chat", "load_ai_callback": load_ai_callback},
        )

        # col3
        if col4.button(
            "✏️",
            key="edit_interaction",
            help="Edit this conversation name",
            use_container_width=False,
        ):
            selected_interaction_pair = st.session_state.get(
                "interaction_summary_selectbox"
            )

            with tab.form(key="edit_interaction_name_form", clear_on_submit=True):
                # col1a, col2a = tab.columns(2)
                st.text_input(
                    "Edit conversation name",
                    key="new_interaction_name",
                    value=selected_interaction_pair.split(":")[1],
                )

                st.form_submit_button(
                    label="Save",
                    # key="save_interaction_name",
                    help="Click to save",
                    type="primary",
                    on_click=update_interaction_name,
                )

        if "confirm_interaction_delete" not in st.session_state:
            st.session_state.confirm_interaction_delete = False

        if st.session_state.confirm_interaction_delete == False:
            col1.button(
                "🗑️",
                help="Delete this conversation",
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
            col1.button(
                "❌",
                help="Click to cancel delete",
                on_click=set_confirm_interaction_delete,
                kwargs={"val": False},
                key=str(uuid.uuid4()),
            )

    except Exception as e:
        logging.error(f"Error loading interaction selectbox: {e}")

    tab.divider()


def set_confirm_interaction_delete(val):
    st.session_state.confirm_interaction_delete = val


def create_interaction(interaction_summary, load_ai_callback = None):
    """Creates an interaction for the current user with the specified summary"""
    
    if "user_id" not in st.session_state:
        # Sometimes this will happen if we're switching controls/screens
        return
    
    new_interaction = str(uuid.uuid4())
    
    Interactions().create_interaction(
        id=new_interaction,
        interaction_summary=interaction_summary,
        user_id=st.session_state.user_id,
    )
    
    if load_ai_callback:
        load_ai_callback(override_interaction_id=new_interaction)


def get_interaction_pairs():
    """Gets the interactions for the current user in 'UUID:STR' format"""
    interactions = None

    if "user_id" in st.session_state:
        interactions = Interactions().get_interactions_by_user_id(
            st.session_state.user_id
        )

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


def get_available_collections():
    # Time the operation:
    start_time = time.time()
    collections = Documents().get_collections()
    total_time = time.time() - start_time

    logging.info(f"get_available_collections() took {total_time} seconds")

    # Create a dictionary of collection id to collection summary
    collections_list = [
        f"{collection.id}:{collection.collection_name} - {collection.collection_type}"
        for collection in collections
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


def get_selected_collection_type():
    collection_id = get_selected_collection_id()
    
    if collection_id == -1:
        return "None"
    
    collection = Documents().get_collection(collection_id)
    
    if not collection:
        return "None"
    
    return collection.collection_type


def get_selected_collection_embedding_model_name():
    collection_type = get_selected_collection_type()
    
    if collection_type.lower().startswith("remote"):
        key = get_app_configuration()["jarvis_ai"]["embedding_models"]["default"][
            "remote"
        ]
    else:
        key = get_app_configuration()["jarvis_ai"]["embedding_models"]["default"][
            "local"
        ]

    return key

def get_selected_collection_configuration():
    key = get_selected_collection_embedding_model_name()

    return get_app_configuration()["jarvis_ai"]["embedding_models"][key]

def get_selected_collection_name():
    """Gets the selected collection name from the selectbox"""
    selected_collection_pair = st.session_state.get("active_collection")

    if not selected_collection_pair:
        return None

    selected_collection_name = selected_collection_pair.split(":")[1]

    return selected_collection_name


def create_collection():
    if st.session_state["new_collection_name"]:
        collection_type = st.session_state.get("new_collection_type", "Local (HF)")

        collection = Documents().create_collection(
            st.session_state["new_collection_name"], collection_type
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

            max_chunk_size = get_selected_collection_configuration()["max_token_length"]

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
                f"*Embedding model: **{get_selected_collection_type()}**, max chunk size: **{max_chunk_size}***"
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
                disabled=(active_collection_id == None or active_collection_id == "-1")
            )
            
            st.markdown("*⚠️ Currently there is no async/queued file ingestion. Do not navigate away from this page, or click on anything else, while the files are being ingested.*")

            status = st.status(f"Ready to ingest", expanded=False, state="complete")

            if uploaded_files and active_collection_id:
                if active_collection_id:
                    if submit_button:
                        ingest_files(
                            uploaded_files=uploaded_files,
                            active_collection_id=active_collection_id,
                            status=status,
                            overwrite_existing_files=st.session_state.get("overwrite_existing_files", True),
                            split_documents=st.session_state.get("split_documents", True),
                            create_chunk_questions=st.session_state.get("create_chunk_questions", False),
                            summarize_chunks=st.session_state.get("summarize_chunks", False),
                            summarize_document=st.session_state.get("summarize_document", False),
                            chunk_size=int(st.session_state.get("file_chunk_size", 500)),
                            chunk_overlap=int(st.session_state.get("file_chunk_overlap", 50)),
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
            documents = load_and_split_documents(
                document_directory=root_temp_dir,
                split_documents=split_documents,
                is_code=is_code,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
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

            document_chunk_length = len(documents)
            st.info(f"Saving {document_chunk_length} document chunks...")
            logging.info(f"Saving {document_chunk_length} document chunks...")

            # For each document, create the file if it doesn't exist and then the document chunks
            current_chunk = 0
            for document in documents:
                current_chunk += 1
                # Get the file name without the root_temp_dir (preserving any subdirectories)
                file_name = (
                    document.metadata["filename"].replace(root_temp_dir, "").strip("/")
                )

                ingest_progress_bar.progress(
                    calculate_progress(len(documents), current_chunk),
                    text=f"Processing document {current_chunk} of {document_chunk_length}",
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
                
                chunk_questions = []
                if create_chunk_questions and hasattr(
                    ai, "generate_chunk_questions"
                ):
                    try:
                        logging.info("Creating questions for chunk...")
                        chunk_questions = ai.generate_chunk_questions(
                            document_text=document.page_content
                        )
                    except Exception as e:
                        logging.error(f"Error creating questions for chunk: {e}")
                        chunk_questions = []
                    
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
                        embedding_model_name=get_selected_collection_embedding_model_name(),
                        question_1=chunk_questions[0] if len(chunk_questions) > 0 else "",
                        question_2=chunk_questions[1] if len(chunk_questions) > 1 else "",
                        question_3=chunk_questions[2] if len(chunk_questions) > 2 else "",
                        question_4=chunk_questions[3] if len(chunk_questions) > 3 else "",
                        question_5=chunk_questions[4] if len(chunk_questions) > 4 else "",
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

    # Done!
    st.balloons()


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
            else:
                st.sidebar.info(f"Version: {version}")
        else:
            st.sidebar.info(f"Version: {version}")

    except Exception as e:
        logging.error(f"Error checking for latest version: {e}")
        st.sidebar.info(f"Version: {version}")


def on_change_collection():
    # Set the last active collection for this interaction (conversation)
    collection_id = get_selected_collection_id()
    interactions_helper = Interactions()
    interactions_helper.update_interaction_collection(
        get_selected_interaction_id(), collection_id
    )


def create_collection_selectbox(ai):
    st.markdown("Selected document collection:")

    col1, col2 = st.columns([0.80, 0.2])

    st.caption(
        "The document collection selected here determines which documents are used to answer questions."
    )

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

    col2.button("➕", help="Create a new document collection", key="show_create_collection")


def refresh_messages_session_state(ai_instance):
    """Pulls the messages from the token buffer on the AI for the first time, and put them into the session state"""

    entire_chat_history = (
        ai_instance.interaction_manager.conversation_token_buffer_memory.chat_memory.messages
    )

    messages_in_memory = (
        ai_instance.interaction_manager.conversation_token_buffer_memory.buffer_as_messages
    )

    logging.info(
        f"Counts for --- `messages_in_memory`: {str(len(messages_in_memory))}, `entire_chat_history`: {str(len(entire_chat_history))}"
    )

    st.session_state["messages"] = []

    for message in entire_chat_history:
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
                st.session_state[f"confirm_conversation_item_delete_{message['id']}"]
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


def handle_chat(main_window_container, ai_instance, configuration):
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
        col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 1, 2, 1, 2])

        help_icon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'

        col1.markdown(
            f'<div align="right" title="Select the mode to use. Auto will automatically switch between a Conversation Only and Tool Using AI based on the users input.">{help_icon} <b>AI Mode:</b></div>', unsafe_allow_html=True
        )

        ai_modes = ["Auto", "Conversation Only"]

        col2.selectbox(
            label="Mode",
            label_visibility="collapsed",
            options=ai_modes,
            index=ai_modes.index(
                get_app_configuration()["jarvis_ai"].get("ai_mode", "Auto")
            ),
            key="ai_mode",
            help="Select the mode to use. 'Auto' will automatically switch between 'Conversation Only' and 'Tool Using AI' based on the user's input.",
            on_change=set_ai_mode,
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
            value=float(
                get_app_configuration()["jarvis_ai"].get("frequency_penalty", 0)
            ),
            step=0.1,
            help="The higher the penalty, the less likely the AI will repeat itself in the completion.",
            on_change=set_frequency_penalty,
            disabled=st.session_state["ai_mode"] != "Conversation Only",
        )

        col5.markdown(
            f'<div align="right" title="Positive values will increase the likelihood of the model talking about new topics by penalizing new tokens that have already been used.">{help_icon} <b>Presence Penalty:</b></div>', unsafe_allow_html=True
        )

        col6.slider(
            label="Presence Penalty",
            label_visibility="collapsed",
            key="presence_penalty",
            min_value=-2.0,
            max_value=2.0,
            value=float(
                get_app_configuration()["jarvis_ai"].get("presence_penalty", 0.6)
            ),
            step=0.1,
            help="The higher the penalty, the more variety of words will be introduced in the completion.",
            on_change=set_presence_penalty,
            disabled=st.session_state["ai_mode"] != "Conversation Only",
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

                if configuration["jarvis_ai"].get("show_llm_thoughts", False):
                    llm_callback = StreamingOnlyCallbackHandler(llm_container)
                    agent_callback = StreamlitCallbackHandler(
                        parent_container=thought_container,
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
                    "search_top_k": int(st.session_state["search_top_k"])
                    if "search_top_k" in st.session_state
                    else 5,
                    "search_type": st.session_state["search_type"]
                    if "search_type" in st.session_state
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
                }
                logging.debug(f"kwargs: {kwargs}")

                try:
                    ai_instance.interaction_manager.agent_callbacks = agent_callbacks
                    ai_instance.interaction_manager.llm_callbacks = llm_callbacks

                    result = ai_instance.query(
                        query=prompt,
                        collection_id=collection_id if collection_id != -1 else None,
                        ai_mode=st.session_state["ai_mode"],
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


def set_jarvis_ai_config_element(key, value):
    configuration = get_app_configuration()

    configuration["jarvis_ai"][key] = value

    ApplicationConfigurationLoader.save_to_file(configuration, get_app_config_path())

    st.session_state["app_config"] = configuration


def set_search_type():
    set_jarvis_ai_config_element("search_type", st.session_state["search_type"])


def set_search_top_k():
    set_jarvis_ai_config_element("search_top_k", st.session_state["search_top_k"])


def set_frequency_penalty():
    set_jarvis_ai_config_element(
        "frequency_penalty", st.session_state["frequency_penalty"]
    )


def set_presence_penalty():
    set_jarvis_ai_config_element(
        "presence_penalty", st.session_state["presence_penalty"]
    )


def set_ai_mode():
    set_jarvis_ai_config_element("ai_mode", st.session_state["ai_mode"])


def update_interaction_name():
    interaction_id = get_selected_interaction_id()
    interaction_name = st.session_state["new_interaction_name"]

    ai: RetrievalAugmentedGenerationAI = st.session_state["rag_ai"]
    ai.interaction_manager.interactions_helper.update_interaction_summary(
        interaction_id=interaction_id,
        interaction_summary=interaction_name,
        needs_summary=False,
    )

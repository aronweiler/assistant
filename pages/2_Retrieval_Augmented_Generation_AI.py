import logging
import os
import uuid

import streamlit as st
from streamlit_extras.stylable_container import stylable_container


from langchain.callbacks.streamlit import StreamlitCallbackHandler

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfigurationLoader,
)

from src.ai.rag_ai import RetrievalAugmentedGenerationAI

from src.db.models.users import Users
from src.db.models.interactions import Interactions
from src.db.models.documents import Documents
from src.db.models.documents import FileModel, DocumentModel

from src.utilities.hash_utilities import calculate_sha256

from src.documents.document_loader import load_and_split_documents


class IngestionSettings:
    def __init__(self):
        self.chunk_size = 500
        self.chunk_overlap = 50
        self.split_documents = True
        self.file_type = "Document"


class RagUI:
    def __init__(self):
        self.users_helper = Users()
        self.interaction_helper = Interactions()
        self.documents_helper = Documents()

    def load_configuration(self):
        """Loads the configuration from the path"""
        rag_config_path = os.environ.get(
            "RAG_CONFIG_PATH",
            "configurations/rag_configs/openai_rag.json",
        )

        if "rag_config" not in st.session_state:
            st.session_state[
                "rag_config"
            ] = RetrievalAugmentedGenerationConfigurationLoader.from_file(
                rag_config_path
            )

    def set_page_config(self):
        """Sets the page configuration"""
        st.set_page_config(
            page_title="Jarvis - Retrieval Augmented Generation AI",
            page_icon="📖",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        st.title("Hey Jarvis 🤖...")

    def ensure_user(self, email):
        """Ensures that a user exists for the given email"""
        self.user_email = email

        user = self.users_helper.get_user_by_email(self.user_email)

        if not user:
            st.markdown(f"Welcome to Jarvis, {self.user_email}! Let's get you set up.")

            # Create the user by showing them a prompt to enter their name, location, age
            name = st.text_input("Enter your name")
            location = st.text_input("Enter your location")

            if st.button("Create Your User!") and name and location:
                user = self.users_helper.create_user(
                    email=self.user_email, name=name, location=location, age=999
                )
                st.experimental_rerun()
            else:
                return False

        else:
            return True

    def set_user_id_from_email(self, user_email):
        """Sets the user_id in the session state from the user's email"""
        users_helper = Users()

        user = users_helper.get_user_by_email(user_email)
        st.session_state["user_id"] = user.id

    def create_interaction(self, interaction_summary):
        """Creates an interaction for the current user with the specified summary"""
        self.interaction_helper.create_interaction(
            id=str(uuid.uuid4()),
            interaction_summary=interaction_summary,
            user_id=st.session_state.user_id,
        )

    def get_interaction_pairs(self):
        """Gets the interactions for the current user in 'UUID:STR' format"""
        interactions = None

        interactions = self.interaction_helper.get_interactions_by_user_id(
            st.session_state.user_id
        )

        if not interactions:
            return None

        # Reverse the list so the most recent interactions are at the top
        interactions.reverse()

        interaction_pairs = [f"{i.id}:{i.interaction_summary}" for i in interactions]

        print(f"get_interaction_pairs: interaction_pairs: {str(interaction_pairs)}")

        return interaction_pairs

    def ensure_interaction(self):
        """Ensures that an interaction exists for the current user"""

        # Only do this if we haven't already done it
        if (
            "interaction_ensured" not in st.session_state
            or not st.session_state["interaction_ensured"]
        ):
            if not self.get_interaction_pairs():
                self.create_interaction("Empty Chat")

            st.session_state["interaction_ensured"] = True

    def load_interaction_selectbox(self):
        """Loads the interaction selectbox"""

        try:
            st.sidebar.selectbox(
                "Select Conversation",
                self.get_interaction_pairs(),
                key="interaction_summary_selectbox",
                format_func=lambda x: x.split(":")[1],
                on_change=self.load_ai,
            )
        except Exception as e:
            logging.error(f"Error loading interaction selectbox: {e}")

    def get_selected_interaction_id(self):
        """Gets the selected interaction id from the selectbox"""
        selected_interaction_pair = st.session_state.get(
            "interaction_summary_selectbox"
        )

        if not selected_interaction_pair:
            return None

        selected_interaction_id = selected_interaction_pair.split(":")[0]

        logging.info(
            f"get_selected_interaction_id: selected_interaction_id: {selected_interaction_id}"
        )

        return selected_interaction_id

    def load_ai(self):
        """Loads the AI instance for the selected interaction id"""
        selected_interaction_id = self.get_selected_interaction_id()

        if "rag_ai" not in st.session_state:
            # First time loading the page
            logging.debug("load_ai: ai not in session state")
            rag_ai_instance = RetrievalAugmentedGenerationAI(
                configuration=st.session_state["rag_config"],
                interaction_id=selected_interaction_id,
                user_email=self.user_email,
                streaming=True,
            )
            st.session_state["rag_ai"] = rag_ai_instance

        elif selected_interaction_id and selected_interaction_id != str(
            st.session_state["rag_ai"].interaction_manager.interaction_id
        ):
            # We have an AI instance, but we need to change the interaction id
            print(
                "load_ai: interaction id is not none and not equal to ai interaction id"
            )
            rag_ai_instance = RetrievalAugmentedGenerationAI(
                configuration=st.session_state["rag_config"],
                interaction_id=selected_interaction_id,
                user_email=self.user_email,
                streaming=True,
            )
            st.session_state["rag_ai"] = rag_ai_instance

    def setup_new_chat_button(self):
        with st.sidebar.container():
            if st.sidebar.button("New Chat", key="new_chat_button"):
                self.create_interaction("Empty Chat")
                st.experimental_rerun()

            st.sidebar.divider()

    def get_available_collections(self, interaction_id) -> dict[str, int]:
        collections = self.documents_helper.get_collections(interaction_id)

        # Create a dictionary of collection id to collection summary
        collections_dict = {
            collection.collection_name: collection.id for collection in collections
        }

        return collections_dict

    def collection_id_from_option(self, option, interaction_id):
        collections_dict = self.get_available_collections(interaction_id)

        if option in collections_dict:
            return collections_dict[option]
        else:
            return None

    def create_collection(self, name):
        selected_interaction_id = self.get_selected_interaction_id()

        print(f"Creating collection {name} (interaction id: {selected_interaction_id})")

        collection = self.documents_helper.create_collection(
            name,
            selected_interaction_id,
        )

        print(f"Created collection {collection.collection_name}")

        return collection.id

    def set_ingestion_settings(self):
        if not st.session_state.ingestion_settings:
            st.session_state.ingestion_settings = IngestionSettings()

        file_type = st.session_state.get("file_type", 0)

        if "Spreadsheet" in file_type:
            st.session_state.ingestion_settings.chunk_size = 250
            st.session_state.ingestion_settings.chunk_overlap = 50
            st.session_state.ingestion_settings.split_documents = True
            st.session_state.ingestion_settings.file_type = "Spreadsheet"
        elif "Code" in file_type:
            st.session_state.ingestion_settings.chunk_size = 0
            st.session_state.ingestion_settings.chunk_overlap = 0
            st.session_state.ingestion_settings.split_documents = False
            st.session_state.ingestion_settings.file_type = "Code"
        else:  # Document
            st.session_state.ingestion_settings.chunk_size = 600
            st.session_state.ingestion_settings.chunk_overlap = 100
            st.session_state.ingestion_settings.split_documents = True
            st.session_state.ingestion_settings.file_type = "Document"

    def create_collections_container(self, main_window_container):
        # Note: The styleable container does not work on firefox yet
#         css_style = """{
#     position: fixed;  /* Keeps the element fixed on the screen */
#     top: 100px;        /* Adjust the top position as needed */
#     right: 50px;      /* Adjust the right position as needed */    
#     max-width: 100%;  /* Ensures the element width doesn't exceed area */
#     z-index: 9999;    /* Ensures the element is on top of other content */
#     max-height: 80vh;     /* Sets the maximum height to 90% of the viewport height */
#     overflow: auto;     /* Adds a scrollbar when the content overflows */
#     overflow-x: hidden;   /* Hides horizontal scrollbar */
# }"""

        selected_interaction_id = self.get_selected_interaction_id()

        with main_window_container:
            #with stylable_container(key="collections_container", css_styles=css_style):
            if "rag_ai" in st.session_state:
                st.caption("Selected document collection:")
                # This is a hack, but it works
                col1, col2 = st.columns([0.80, 0.2])
                col1.selectbox(
                    "Active document collection",
                    self.get_available_collections(selected_interaction_id),
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
                    new_collection = col2.button(
                        "Create New", key="create_collection"
                    )

                    if st.session_state["new_collection_name"] and new_collection:
                        self.create_collection(
                            st.session_state["new_collection_name"]
                        )
                        st.experimental_rerun()

                if "rag_ai" in st.session_state:
                    option = st.session_state["active_collection"]
                    if option:
                        collection_id = self.collection_id_from_option(
                            option, selected_interaction_id
                        )

                        st.session_state.rag_ai.interaction_manager.collection_id = collection_id

                        loaded_docs = st.session_state.rag_ai.interaction_manager.get_loaded_documents_for_display()
                        loaded_docs_delimited = st.session_state.rag_ai.interaction_manager.get_loaded_documents_delimited()
                        
                        with st.expander(
                            label=f"({len(loaded_docs)}) documents in {option}",
                            expanded=False,
                        ):
                            for doc in loaded_docs:
                                st.write(doc)

                        # expanded = False
                        # try:
                        #     expanded = loaded_docs != None and len(loaded_docs) > 0
                        # except:
                        #     pass

                        st.markdown("### RAG Options")

                        with st.expander("Search"): #, expanded=expanded):
                            st.radio("Text search method", ["Similarity", "Keyword"], key="search_method", index=0)
                            st.number_input("Top K (number of document chunks to use in searches)", key="search_top_k", value=5)
                            st.selectbox(
                                "Summarization strategy",
                                ['map_reduce', 'refine'],
                                key="summarization_strategy"
                            )
                        
                        with st.expander("Spreadsheets"):
                            st.toggle("Use Pandas for Spreadsheets", key="use_pandas", value=True)     
                        
                        with st.expander("General"):                           
                            st.selectbox(
                                "Override automatic document selection:",
                                ['0:---'] + loaded_docs_delimited,
                                key="override_file",
                                format_func=lambda x: x.split(":")[1],
                            )
                            st.number_input("Timeout (seconds)", key="agent_timeout", value=120)
                        
                        tools = st.session_state.rag_ai.get_all_tools()

                        def toggle_tool(tool_name):
                            st.session_state.rag_ai.toggle_tool(tool_name)

                        with st.expander("Available RAG Tools"):
                            for tool in tools:
                                st.toggle(tool['name'], key=tool['name'], help=tool['about'], value=tool['enabled'], on_change=toggle_tool, kwargs={'tool_name': tool['name']})                            
                    else:
                        st.warning("No collection selected")

            st.write("")
            st.write("")
            st.write("")
            st.write("")

    def select_documents(self):
        with st.sidebar.container():
            active_collection = st.session_state.get("active_collection")

            upload_form = st.form("upload_files_form", clear_on_submit=True)
            uploaded_files = upload_form.file_uploader(
                "Choose your files",
                accept_multiple_files=True,
                disabled=(active_collection == None),
                key="file_uploader",
            )

            with st.expander(
                "Ingestion Options",
                expanded=uploaded_files != None and len(uploaded_files) > 0,
            ):
                st.radio(
                    "File type",
                    [
                        "Document (Word, PDF, TXT)",
                        "Spreadsheet (XLS, CSV)",
                        "Code (Python, C++)",
                    ],
                    key="file_type",
                    on_change=self.set_ingestion_settings,
                )

                # Handle the first time
                if not "ingestion_settings" in st.session_state:
                    st.session_state.ingestion_settings = IngestionSettings()

                st.toggle(
                    "Overwrite existing files",
                    key="overwrite_existing_files",
                    value=False,
                )

                st.toggle(
                    "Split documents",
                    key="split_documents",
                    value=st.session_state.ingestion_settings.split_documents,
                )
                st.text_input(
                    "Chunk size",
                    key="file_chunk_size",
                    value=st.session_state.ingestion_settings.chunk_size,
                )
                st.text_input(
                    "Chunk overlap",
                    key="file_chunk_overlap",
                    value=st.session_state.ingestion_settings.chunk_overlap,
                )

            status = st.status(f"File status", expanded=False, state="complete")

            submit_button = upload_form.form_submit_button("Ingest files")

            if uploaded_files and active_collection:
                collection_id = None

                if active_collection:
                    collection_id = self.collection_id_from_option(
                        active_collection,
                        st.session_state["rag_ai"].interaction_manager.interaction_id,
                    )

                    if submit_button:
                        self.ingest_files(
                            uploaded_files,
                            active_collection,
                            collection_id,
                            status,
                            st.session_state.get("overwrite_existing_files", True),
                            st.session_state.get("split_documents", True),
                            int(st.session_state.get("file_chunk_size", 500)),
                            int(st.session_state.get("file_chunk_overlap", 50)),
                        )

    def ingest_files(
        self,
        uploaded_files,
        active_collection,
        collection_id,
        status,
        overwrite_existing_files,
        split_documents,
        chunk_size,
        chunk_overlap,
    ):
        """Ingests the uploaded files into the specified collection"""
        if not active_collection:
            st.error("No collection selected")
            return

        if not uploaded_files:
            st.error("No files selected")
            return

        if not collection_id:
            st.error("No collection id found")
            return

        status.update(
            label=f"Ingesting files and adding to '{active_collection}'",
            state="running",
        )

        # First upload the files to our temp directory
        uploaded_file_paths, root_temp_dir = self.upload_files(uploaded_files, status)

        with status.container() as status_container:
            with st.empty():
                st.info(f"Processing {len(uploaded_file_paths)} files...")
                # First see if there are any files we can't load
                files = []
                for uploaded_file_path in uploaded_file_paths:
                    # Get the file name
                    file_name = (
                        uploaded_file_path.replace(root_temp_dir, "")
                        .strip("/")
                        .strip("\\")
                    )

                    st.info(f"Verifying {uploaded_file_path}...")

                    # See if it exists in this collection
                    existing_file = self.documents_helper.get_file_by_name(
                        file_name, collection_id
                    )

                    if existing_file and not overwrite_existing_files:
                        st.error(
                            f"File '{file_name}' already exists, and overwrite is not enabled"
                        )
                        status.update(
                            label=f"File '{file_name}' already exists, and overwrite is not enabled",
                            state="error",
                        )

                        return

                    if existing_file and overwrite_existing_files:
                        # Delete the document chunks
                        self.documents_helper.delete_document_chunks_by_file_id(
                            existing_file.id
                        )

                        # Delete the existing file
                        self.documents_helper.delete_file(existing_file.id)

                    # Read the file
                    with open(uploaded_file_path, "rb") as file:
                        file_data = file.read()

                    # Create the file
                    files.append(
                        self.documents_helper.create_file(
                            FileModel(
                                user_id=st.session_state.user_id,
                                collection_id=collection_id,
                                file_name=file_name,
                                file_hash=calculate_sha256(uploaded_file_path),
                                file_data=file_data,
                                file_classification=st.session_state.ingestion_settings.file_type,
                            )
                        )
                    )

                st.info("Splitting documents...")

                # Pass the root temp dir to the ingestion function
                documents = load_and_split_documents(
                    root_temp_dir,
                    split_documents,
                    chunk_size,
                    chunk_overlap,
                )

                st.info(f"Saving {len(documents)} document chunks...")

                # For each document, create the file if it doesn't exist and then the document chunks
                for document in documents:
                    # Get the file name without the root_temp_dir (preserving any subdirectories)
                    file_name = (
                        document.metadata["filename"]
                        .replace(root_temp_dir, "")
                        .strip("/")
                    )

                    # Get the file reference
                    file = next((f for f in files if f.file_name == file_name), None)

                    if not file:
                        status_container.error(
                            f"Could not find file '{file_name}' in the database after uploading"
                        )
                        break

                    # Create the document chunks
                    self.documents_helper.store_document(
                        DocumentModel(
                            collection_id=collection_id,
                            file_id=file.id,
                            user_id=st.session_state.user_id,
                            document_text=document.page_content,
                            additional_metadata=document.metadata,
                            document_name=document.metadata["filename"],
                        )
                    )

                st.success(
                    f"Successfully ingested {len(documents)} document chunks from {len(files)} files"
                )
                status.update(
                    label=f"✅ Ingestion complete",
                    state="complete",
                )

    def upload_files(self, uploaded_files, status):
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

    def refresh_messages_session_state(self, rag_ai_instance):
        """Pulls the messages from the token buffer on the AI for the first time, and put them into the session state"""

        buffer_messages = (
            rag_ai_instance.interaction_manager.conversation_token_buffer_memory.buffer_as_messages
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

    def show_old_messages(self, rag_ai_instance):
        self.refresh_messages_session_state(rag_ai_instance)

        for message in st.session_state["messages"]:
            with st.chat_message(message["role"], avatar=message["avatar"]):
                st.markdown(message["content"])

    def handle_chat(self, main_window_container):
        with main_window_container.container():
            # Get the AI instance from session state
            if "rag_ai" not in st.session_state:
                st.warning("No AI instance found in session state")
                st.stop()
            else:
                rag_ai_instance = st.session_state["rag_ai"]

            self.show_old_messages(rag_ai_instance)

            st.write("")
            st.write("")
            st.write("")
            st.write("")

        # Get user input (must be outside of the container)
        prompt = st.chat_input("Enter your message here", key="chat_input")        

        if prompt:
            with main_window_container.container():
                st.chat_message("user", avatar="👤").markdown(prompt)

                with st.chat_message("assistant", avatar="🤖"):
                    thought_container = st.container().empty()
                    llm_container = st.container().empty()
                    callbacks = []
                    callbacks.append(
                        StreamlitCallbackHandler(
                            parent_container=thought_container,
                            expand_new_thoughts=True,
                            collapse_completed_thoughts=True,
                        )
                    )

                    collection_id = self.collection_id_from_option(
                        st.session_state["active_collection"],
                        rag_ai_instance.interaction_manager.interaction_id,
                    )

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
                        if "override_file" in st.session_state and st.session_state["override_file"].split(":")[0] != "0"
                        else None,
                        "agent_timeout": int(st.session_state["agent_timeout"])
                        if "agent_timeout" in st.session_state
                        else 120,
                        "summarization_strategy": st.session_state["summarization_strategy"]
                        if "summarization_strategy" in st.session_state
                        else "map_reduce",
                    }

                    result = rag_ai_instance.query(
                        query=prompt,
                        collection_id=collection_id,
                        agent_callbacks=callbacks,
                        kwargs=kwargs,
                    )

                    print(f"Result: {result}")

                    llm_container.markdown(result)

                


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    rag_ui = RagUI()

    # Always comes first!
    rag_ui.load_configuration()

    rag_ui.set_page_config()

    # Get the user from the environment variables
    user_email = os.environ.get("USER_EMAIL", None)

    if not user_email:
        raise ValueError("USER_EMAIL environment variable not set")

    if rag_ui.ensure_user(user_email):
        rag_ui.set_user_id_from_email(user_email)
        rag_ui.ensure_interaction()
        rag_ui.load_interaction_selectbox()
        # Set up columns for chat and collections
        col1, col2 = st.columns([0.65, 0.35])

        rag_ui.load_ai()
        rag_ui.setup_new_chat_button()
        rag_ui.create_collections_container(col2)

        rag_ui.select_documents()

        rag_ui.handle_chat(col1)

        css = '''
<style>
    section.main>div {
        padding-bottom: 1rem;
    }
    [data-testid="column"]>div>div {
        max-height: 70vh;
        overflow-y: auto;
    }
</style>
'''

st.markdown(css, unsafe_allow_html=True)

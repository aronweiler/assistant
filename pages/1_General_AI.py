import logging
import uuid
import shutil
import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from streamlit_extras.grid import grid
import os

# from langchain.callbacks import StreamlitCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler

from src.ai.request_router import RequestRouter

from src.configuration.assistant_configuration import AssistantConfigurationLoader



from src.db.models.interactions import Interactions
from src.db.models.documents import Documents
from src.db.models.users import Users
from src.db.models.domain.file_model import FileModel
from src.db.models.domain.document_model import DocumentModel

from src.documents.document_loader import load_and_split_documents

from src.runners.ui.streamlit_agent_callback import StreamlitAgentCallbackHandler

from src.ai.llm_helper import get_prompt
from src.utilities.hash_utilities import calculate_sha256
from src.ai.callbacks.streamlit_callbacks import StreamlitStreamHandler

class GeneralUI:
    def get_configuration_path(self):
        return os.environ.get(
            "ASSISTANT_CONFIG_PATH",
            "configurations/console_configs/console_ai.json",
        )

    def get_available_collections(self, interaction_id) -> dict[str, int]:
        documents_helper = Documents()

        collections = documents_helper.get_collections(interaction_id)

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

        documents_helper = Documents()
        collection = documents_helper.create_collection(
            name,
            selected_interaction_id,
        )

        print(f"Created collection {collection.collection_name}")

        return collection.id

    def create_collections_container(self, main_window_container):
        css_style = """{
    position: fixed;  /* Keeps the element fixed on the screen */
    top: 10px;        /* Adjust the top position as needed */
    right: 10px;      /* Adjust the right position as needed */
    width: 300px;     /* Adjust the width as needed */
    max-width: 100%;  /* Ensures the element width doesn't exceed area */
    z-index: 9999;    /* Ensures the element is on top of other content */
    max-height: 80vh;     /* Sets the maximum height to 90% of the viewport height */
    overflow: auto;     /* Adds a scrollbar when the content overflows */
    overflow-x: hidden;   /* Hides horizontal scrollbar */
}"""

        selected_interaction_id = self.get_selected_interaction_id()

        with main_window_container:
            with stylable_container(key="collections_container", css_styles=css_style):
                if "ai" in st.session_state:
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

                        if (
                            st.session_state.get("new_collection_name")
                            and new_collection
                        ):
                            self.create_collection(
                                st.session_state["new_collection_name"]
                            )

                    if "ai" in st.session_state:
                        option = st.session_state["active_collection"]
                        if option:
                            collection_id = self.collection_id_from_option(
                                option, selected_interaction_id
                            )

                            st.session_state[
                                "ai"
                            ].interaction_manager.collection_id = collection_id

                            loaded_docs = st.session_state[
                                "ai"
                            ].interaction_manager.get_loaded_documents_for_display()

                            with st.expander("File Search Options", expanded=False):
                                st.text_input("Top K", key="search_top_k", value=10)

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

    def get_interaction_pairs(self):
        """Gets the interactions for the current user in 'UUID:STR' format"""
        interactions_helper = Interactions()

        interactions = None

        user_id = self.set_user_id_from_email()

        interactions = interactions_helper.get_interactions_by_user_id(user_id)

        if not interactions:
            return None

        # Reverse the list so the most recent interactions are at the top
        interactions.reverse()

        interaction_pairs = [f"{i.id}:{i.interaction_summary}" for i in interactions]

        print(f"get_interaction_pairs: interaction_pairs: {str(interaction_pairs)}")

        return interaction_pairs

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
            print(f"Error loading interaction selectbox: {e}")

    def get_selected_interaction_id(self):
        """Gets the selected interaction id from the selectbox"""
        selected_interaction_pair = st.session_state.get(
            "interaction_summary_selectbox"
        )

        if not selected_interaction_pair:
            return None

        selected_interaction_id = selected_interaction_pair.split(":")[0]

        print(
            f"get_selected_interaction_id: selected_interaction_id: {selected_interaction_id}"
        )

        return selected_interaction_id

    def load_ai(self):
        """Loads the AI instance for the selected interaction id"""
        selected_interaction_id = self.get_selected_interaction_id()

        if "ai" not in st.session_state:
            # First time loading the page
            print("load_ai: ai not in session state")
            ai_instance = RequestRouter(
                st.session_state["config"],
                user_email,
                selected_interaction_id,
                streaming=True,
            )
            st.session_state["ai"] = ai_instance

        elif selected_interaction_id and selected_interaction_id != str(
            st.session_state["ai"].interaction_manager.interaction_id
        ):
            # We have an AI instance, but we need to change the interaction id
            print(
                "load_ai: interaction id is not none and not equal to ai interaction id"
            )
            ai_instance = RequestRouter(
                st.session_state["config"],
                user_email,
                selected_interaction_id,
                streaming=True,
            )
            st.session_state["ai"] = ai_instance

    def select_conversation(self):
        with st.sidebar.container():
            new_chat_button_clicked = st.sidebar.button(
                "New Chat", key="new_chat_button"
            )

            if new_chat_button_clicked:
                self.create_interaction("Empty Chat")

    def select_documents(self):
        with st.sidebar.container():
            st.toggle("Show LLM thoughts", key="show_llm_thoughts", value=True)

            active_collection = st.session_state.get("active_collection")

            uploaded_files = st.file_uploader(
                "Choose your files",
                accept_multiple_files=True,
                disabled=(active_collection == None),
                key="file_uploader",
            )

            status = st.status(f"File status", expanded=False, state="complete")

            if uploaded_files and active_collection:
                collection_id = None

                if active_collection:
                    collection_id = self.collection_id_from_option(
                        active_collection,
                        st.session_state["ai"].interaction_manager.interaction_id,
                    )
                    print(f"Active collection: {active_collection}")

                with st.expander("File Ingestion Options", expanded=False):
                    st.toggle(
                        "Overwrite existing files",
                        key="overwrite_existing_files",
                        value=True,
                    )
                    st.toggle("Split documents", key="split_documents", value=True)
                    st.text_input("Chunk size", key="file_chunk_size", value=500)
                    st.text_input("Chunk overlap", key="file_chunk_overlap", value=50)

                if (
                    active_collection
                    and st.button("Ingest files")
                    and len(uploaded_files) > 0
                ):
                    self.ingest_files(
                        uploaded_files,
                        active_collection,
                        collection_id,
                        status,
                        st.session_state["overwrite_existing_files"],
                        st.session_state["split_documents"],
                        int(st.session_state.get("file_chunk_size", 500)),
                        int(st.session_state.get("file_chunk_overlap", 50)),
                    )

    def clear_to_create_file_and_docs(self, file_name, file_hash, collection_id, overwrite_existing_files) -> bool:
        documents_helper = Documents()

        existing_file = documents_helper.get_file_by_name(file_name, collection_id)        
            
        if existing_file is not None:
            # File already exists

            if overwrite_existing_files:
                logging.info(
                    f"Attempting to overwrite file: {file_name} in collection: {collection_id}"
                )

                # Did we find a file, and does it have a different hash?
                if existing_file.file_hash != file_hash:
                    # Delete all of the document chunks associated with this file
                    documents_helper.delete_document_chunks_by_file_id(existing_file.id)

                    # Delete the file itself
                    documents_helper.delete_file(existing_file.id)
                else:
                    logging.info(
                        f"Skipping overwrite- File: {file_name} in collection: {collection_id} already exists, and has the same hash"
                    )
                    st.info(f"Skipping overwrite- File: {file_name} in collection: {collection_id} already exists, and has the same hash")

                    # Returning false indicates that no file was created, so we shouldn't load documents
                    return False
            else:
                if existing_file.file_hash != file_hash:
                    raise ValueError(
                        f"File with name: {file_name} already exists in collection: {collection_id}, but has a different hash"
                    )
                else:
                    logging.info(
                        f"File: {file_name} in collection: {collection_id} already exists, and has the same hash"
                    )
                    st.info(f"Skipping load: File: {file_name} in collection: {collection_id} already exists, and has the same hash")                    

                    # Returning false indicates that no file was created, so we shouldn't load documents
                    return False
        
        return True
    
    def upload_files(self, uploaded_files, status):
        root_temp_dir = "temp"

        if not os.path.exists(root_temp_dir):
            os.makedirs(root_temp_dir)

        # First upload all of the files- this needs to be done before we process them, in case there are inter-dependencies
        uploaded_file_paths = []
        for uploaded_file in uploaded_files:
            with status.empty():
                with st.container():
                    st.info(f"Uploading file: {uploaded_file.name}")
                    # Create a unique path for each file- because files can and will get split into multiples (e.g. Split into CSVs for excel files)
                    file_path = os.path.join(root_temp_dir, str(uuid.uuid4()), uploaded_file.name)                                                
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    uploaded_file_paths.append(file_path)

        return uploaded_file_paths

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
        status.update(
            label=f"Ingesting files and adding to {active_collection}",
            state="running",
        )

        try:
            # First upload the files to our temp directory
            uploaded_file_paths = self.upload_files(uploaded_files, status)

            documents_helper = Documents()

            with status.empty():
                with st.container():
                    st.info(f"Processing files... please wait.")

                    # Go through each file and see if it already exists, then split and upload the chunks
                    
                    for uploaded_file_path in uploaded_file_paths:
                        file_name = os.path.basename(uploaded_file_path)
                        file_directory = os.path.dirname(uploaded_file_path)
                        
                        with open(uploaded_file_path, 'rb') as file:
                            file_data = file.read()

                        file_hash = calculate_sha256(uploaded_file_path)                        
                        
                        clear_to_create = self.clear_to_create_file_and_docs(file_name, file_hash, collection_id, overwrite_existing_files)

                        if clear_to_create:
                            documents = load_and_split_documents(
                                file_directory, split_documents, chunk_size, chunk_overlap
                            )

                            # Since files can be split into multiples, we need to get a new list of file names
                            file_names = list(set([d.metadata["filename"] for d in documents]))

                            for file_name in file_names:

                                if len(file_names) > 1:
                                    # That means we also have to re-run the clear check
                                    # This whole step should be refactored so it takes place at a higher level or something where we 
                                    # don't have to split the documents up first
                                    file_hash = calculate_sha256(uploaded_file_path)                            
                                    if not self.clear_to_create_file_and_docs(file_name, file_hash, collection_id, overwrite_existing_files):                                        
                                        continue

                                    st.info(f"The file {file_name} was split into multiple files ({len(file_names)}), so we're creating a new file for each one")
                                
                                file = documents_helper.create_file(
                                    FileModel(
                                        collection_id,
                                        user_id=st.session_state["user_id"],
                                        file_name=file_name,
                                        file_hash=calculate_sha256(os.path.join(file_directory, file_name)),
                                        file_data=file_data
                                    )
                                )

                                st.info(f"Loading {len(documents)} chunks for {file_name}")
                            
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

                                self.classify_file(documents_helper, documents, file)                        

                        

                    status.empty()
                    status.update(
                        label=f"✅ Document ingestion complete!",
                        state="complete",
                        expanded=False,
                    )

                    uploaded_files.clear()

        except Exception as e:
            # debugging streamlit
            # raise e
            logging.error(e)
            print(e)
            status.error(f"Error: {e}", icon="❌")
            status.update(
                label=f"Document ingestion failed!",
                state="error",
                expanded=False,
            )

            try:
                shutil.rmtree("temp")
                print(f"Deleted temporary directory")
            except Exception as e:
                print(f"Error deleting temporary directory: {e}")

    def classify_file(
        self, documents_helper: Documents, documents, file
    ):
        # Use up to the first 10 document chunks to classify this document

        text = "\n".join([d.page_content for d in documents[:10]])
        file.file_classification = documents[0].metadata.get(
            "classification", "Document"
        )

        ai_instance: RequestRouter = st.session_state["ai"]

        summarize_string = get_prompt(
            ai_instance.assistant_configuration.request_router.model_configuration.llm_type,
            "CONCISE_SUMMARIZE_TEMPLATE",
        ).format(text=text)

        file.file_summary = ai_instance.llm.predict(summarize_string)        

        documents_helper.update_file_summary_and_class(
            file.id, file.file_summary, file.file_classification
        )

        print(
            f"File summary: {file.file_summary}, classification: {file.file_classification}"
        )

    def refresh_messages_session_state(self, ai_instance):
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

    def show_old_messages(self, ai_instance):
        self.refresh_messages_session_state(ai_instance)

        for message in st.session_state["messages"]:
            with st.chat_message(message["role"], avatar=message["avatar"]):
                st.markdown(message["content"])

    # TODO: Replace the DB backed chat history with a cached one here!
    def handle_chat(self, main_window_container):
        with main_window_container.container():
            # Get the AI instance from session state
            if "ai" not in st.session_state:
                st.warning("No AI instance found in session state")
                st.stop()
            else:
                ai_instance = st.session_state["ai"]

            self.show_old_messages(ai_instance)

        # Get user input (must be outside of the container)
        prompt = st.chat_input("Enter your message here", key="chat_input")

        if prompt:
            with main_window_container.container():
                st.chat_message("user", avatar="👤").markdown(prompt)

                with st.chat_message("assistant", avatar="🤖"):
                    llm_callbacks = []
                    llm_callbacks.append(StreamlitStreamHandler(st.container().empty()))

                    agent_callbacks = []
                    if st.session_state["show_llm_thoughts"]:
                        print("showing agent thoughts")
                        agent_callback_container = st.container().empty()
                        agent_callback = StreamlitAgentCallbackHandler(
                            agent_callback_container,
                            expand_new_thoughts=True,
                            collapse_completed_thoughts=True,
                        )
                        agent_callbacks.append(agent_callback)

                    collection_id = self.collection_id_from_option(
                        st.session_state["active_collection"],
                        ai_instance.interaction_manager.interaction_id,
                    )

                    kwargs = {
                        "search_top_k": int(st.session_state["search_top_k"])
                        if "search_top_k" in st.session_state
                        else 10
                    }

                    result = ai_instance.query(
                        prompt,
                        collection_id=collection_id,
                        llm_callbacks=llm_callbacks,
                        agent_callbacks=agent_callbacks,
                        kwargs=kwargs,
                    )

                    print(f"Result: {result}")

                    st.markdown(result)

    def ensure_user(self, email):
        self.user_email = email

        users_helper = Users()

        user = users_helper.get_user_by_email(self.user_email)

        if not user:
            st.markdown(f"Welcome to Jarvis, {self.user_email}! Let's get you set up.")

            # Create the user by showing them a prompt to enter their name, location, age
            name = st.text_input("Enter your name")
            location = st.text_input("Enter your location")

            if (
                name and location
            ):  # Check if both name and location inputs are not empty
                if st.button("Create Your User!"):
                    user = users_helper.create_user(
                        email=self.user_email, name=name, location=location, age=999
                    )
                else:
                    return False
            else:
                return False
        else:
            return True

    def set_user_id_from_email(self):
        users_helper = Users()

        user = users_helper.get_user_by_email(self.user_email)
        st.session_state["user_id"] = user.id

        return user.id

    def create_interaction(self, interaction_summary):
        interactions_helper = Interactions()

        interactions_helper.create_interaction(
            id=str(uuid.uuid4()),
            interaction_summary=interaction_summary,
            user_id=st.session_state["user_id"],
        )

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

    def load_configuration(self):
        # Load environment variables from the .env file
        # load_dotenv("/Repos/assistant/.env")

        assistant_config_path = self.get_configuration_path()
        if "config" not in st.session_state:
            st.session_state["config"] = AssistantConfigurationLoader.from_file(
                assistant_config_path
            )

    def set_page_config(self):
        st.set_page_config(
            page_title="Jarvis - General",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        st.title("Hey Jarvis 🤖...")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    streamlit_ui = GeneralUI()

    # Always comes first!
    streamlit_ui.load_configuration()

    streamlit_ui.set_page_config()

    # Get the user from the environment variables
    user_email = os.environ.get("USER_EMAIL", None)

    if not user_email:
        raise ValueError("USER_EMAIL environment variable not set")

    if streamlit_ui.ensure_user(user_email):
        streamlit_ui.set_user_id_from_email()

        streamlit_ui.ensure_interaction()

        streamlit_ui.load_interaction_selectbox()

        # Set up columns for chat and collections
        col1, col2 = st.columns([0.65, 0.35])

        print("loading ai")
        streamlit_ui.load_ai()

        print("selecting conversation")
        streamlit_ui.select_conversation()

        print("creating collections container")
        streamlit_ui.create_collections_container(col2)

        print("selecting documents")
        streamlit_ui.select_documents()

        print("handling chat")
        streamlit_ui.handle_chat(col1)

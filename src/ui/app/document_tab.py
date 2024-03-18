import logging
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from shared.database.models.user_settings import UserSettings
from src.shared.database.models.conversations import Conversations
from src.shared.database.models.documents import Documents
import streamlit_shared as streamlit_shared
from src.shared.utilities.configuration_utilities import get_app_configuration


def create_documents_collection_tab(ai, tab: DeltaGenerator, widget_key: str, show_new_button: bool = False):
    with tab:
        st.markdown("Selected document collection:")

        
        if not show_new_button:
            st.caption(
                "The document collection selected here determines which documents are used to answer questions."
            )
        else:
            st.caption(
                "The document collection selected here is where any new documents you upload will reside."
            )
        
        col1, col2 = st.columns([0.80, 0.2])

        available_collections = get_available_collections()
        selected_collection_id_index = 0
        # Find the index of the selected collection
        for i, collection in enumerate(available_collections):
            conversation = ai.conversation_manager.get_conversation()

            if conversation is None:
                selected_collection_id_index = -1
                break

            if int(collection.split(":")[0]) == int(
                ai.conversation_manager.get_conversation().last_selected_collection_id
            ):
                selected_collection_id_index = i
                break
            
        col = col1 if show_new_button else tab

        col.selectbox(
            label="Active document collection",
            index=int(selected_collection_id_index),
            options=available_collections,
            key=widget_key,
            placeholder="Select a collection",
            label_visibility="collapsed",
            format_func=lambda x: x.split(":")[1],
            on_change=on_change_collection,
        )

        # Create a form for the collection creation:
        if show_new_button:
            if col2.button(
                "➕", help="Create a new document collection", key=f"{widget_key}_new"
            ):
                with st.form(key="new_collection", clear_on_submit=True):
                    st.text_input(
                        "New collection name",
                        key=f"{widget_key}_new_collection_name",
                    )

                    # get the list of embedding models
                    embedding_models = get_app_configuration()["jarvis_ai"][
                        "embedding_models"
                    ]["available"]

                    st.selectbox(
                        "New collection embedding type",
                        options=[e for e in embedding_models],
                        key="new_embedding_name",
                    )

                    st.form_submit_button(
                        "Create New Collection",
                        type="primary",
                        on_click=create_collection,
                    )

        

        # TODO: Put this into the general settings area
        # st.divider()
        # with st.expander("Advanced"):
        #     st.number_input(
        #         "Timeout (seconds)",
        #         help="The amount of time to wait for a response from the AI",
        #         key="agent_timeout",
        #         value=600,
        #     )

        #     st.number_input(
        #         "Maximum AI iterations",
        #         help="The number of recursive (or other) iterations the AI will perform (usually tool calls).",
        #         key="max_iterations",
        #         value=25,
        #     )


def get_available_collections():
    # Time the operation:
    collections = Documents().get_collections(user_id=st.session_state.user_id)

    # Create a dictionary of collection id to collection name
    collections_list = [
        f"{collection.id}:{collection.collection_name} - {collection.embedding_name}"
        for collection in collections
    ]

    collections_list.insert(0, "-1:---")

    return collections_list


def create_collection():
    if st.session_state["file_upload_collection_selectbox_new_collection_name"]:
        embedding_name = st.session_state.get("new_embedding_name", "Local (HF)")

        try:
            collection = Documents().create_collection(
                collection_name=st.session_state["file_upload_collection_selectbox_new_collection_name"],
                embedding_name=embedding_name,
                user_id=st.session_state.user_id,
            )

            logging.info(
                f"New collection created: {collection.id} - {collection.collection_name}"
            )

            if "rag_ai" in st.session_state:
                st.session_state.rag_ai.conversation_manager.collection_id = (
                    collection.id
                )
                st.session_state.rag_ai.conversation_manager.conversations_helper.update_conversation_collection(
                    streamlit_shared.get_selected_conversation_id(), collection.id
                )

            return collection.id
        except Exception as e:

            logging.error(f"Error creating collection: {e}")
            st.error(
                "Error creating collection, please ensure the collection name is unique."
            )


def on_change_collection():
    # Set the last active collection for this conversation (conversation)
    collection_id = streamlit_shared.get_selected_collection_id()
    interactions_helper = Conversations()
    interactions_helper.update_conversation_collection(
        streamlit_shared.get_selected_conversation_id(), collection_id
    )
    st.session_state.rag_ai.conversation_manager.collection_id = collection_id

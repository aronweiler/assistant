import logging
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from src.db.models.conversations import Conversations
from src.db.models.documents import Documents
import src.ui.streamlit_shared as streamlit_shared


def create_documents_collection_tab(ai, tab: DeltaGenerator):
    with tab:
        st.markdown("Selected document collection:")

        col1, col2 = st.columns([0.80, 0.2])

        st.caption(
            "The document collection selected here determines which documents are used to answer questions."
        )

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

        show_create_collection = col2.button(
            "➕", help="Create a new document collection", key="show_create_collection"
        )

        # Create a form for the collection creation:
        if show_create_collection:
            with st.form(key="new_collection", clear_on_submit=True):
                st.text_input(
                    "New collection name",
                    key="new_collection_name",
                )

                st.selectbox(
                    "New collection embedding type",
                    options=["Remote (OpenAI)", "Local (HF)"],
                    key="new_collection_type",
                )

                st.form_submit_button(
                    "Create New Collection",
                    type="primary",
                    on_click=create_collection,
                )

        selected_collection_id = streamlit_shared.get_selected_collection_id()
        if "rag_ai" in st.session_state and selected_collection_id != '-1':
            loaded_docs = (
                st.session_state.rag_ai.conversation_manager.get_loaded_documents_for_display()
            )

            with st.expander(
                label=f"({len(loaded_docs)}) documents in {streamlit_shared.get_selected_collection_name()}",
                expanded=False,
            ):
                # TODO: Add capabilities to edit the collection (delete documents)
                for doc in loaded_docs:
                    st.write(doc)


def get_available_collections():
    # Time the operation:
    collections = Documents().get_collections()

    # Create a dictionary of collection id to collection name
    collections_list = [
        f"{collection.id}:{collection.collection_name} - {collection.collection_type}"
        for collection in collections
    ]

    collections_list.insert(0, "-1:---")

    return collections_list


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
            st.session_state.rag_ai.conversation_manager.collection_id = collection.id
            st.session_state.rag_ai.conversation_manager.conversations_helper.update_conversation_collection(
                streamlit_shared.get_selected_conversation_id(), collection.id
            )

        return collection.id


def on_change_collection():
    # Set the last active collection for this conversation (conversation)
    collection_id = streamlit_shared.get_selected_collection_id()
    interactions_helper = Conversations()
    interactions_helper.update_conversation_collection(
        streamlit_shared.get_selected_conversation_id(), collection_id
    )
    st.session_state.rag_ai.conversation_manager.collection_id = collection_id
    

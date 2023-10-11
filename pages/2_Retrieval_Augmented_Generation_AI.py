import logging
import os
import uuid

import streamlit as st
from streamlit_extras.stylable_container import stylable_container


from langchain.callbacks.streamlit import StreamlitCallbackHandler
from src.ai.callbacks.generic_callbacks import ResultOnlyCallbackHandler

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfigurationLoader,
)

from src.ai.rag_ai import RetrievalAugmentedGenerationAI

import src.ui.streamlit_shared as ui_shared


class RagUI:
    def __init__(self):
        self.user_email = None

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

    def load_ai(self):
        """Loads the AI instance for the selected interaction id"""
        selected_interaction_id = ui_shared.get_selected_interaction_id()

        if "rag_ai" not in st.session_state:
            # First time loading the page
            logging.debug("load_ai: no ai in session state, creating a new one")
            rag_ai_instance = RetrievalAugmentedGenerationAI(
                configuration=st.session_state["rag_config"],
                interaction_id=selected_interaction_id,
                user_email=self.user_email,
                streaming=True,
            )
            st.session_state["rag_ai"] = rag_ai_instance
            logging.debug("load_ai: created new ai instance")

        elif selected_interaction_id and selected_interaction_id != str(
            st.session_state["rag_ai"].interaction_manager.interaction_id
        ):
            logging.debug(
                f"load_ai: AI instance exists, but need to change interaction ID from {str(st.session_state['rag_ai'].interaction_manager.interaction_id)} to {selected_interaction_id}"
            )
            # We have an AI instance, but we need to change the interaction id
            rag_ai_instance = RetrievalAugmentedGenerationAI(
                configuration=st.session_state["rag_config"],
                interaction_id=selected_interaction_id,
                user_email=self.user_email,
                streaming=True,
            )
            st.session_state["rag_ai"] = rag_ai_instance

    def create_collections_container(self, main_window_container):
        css_style = """{
    position: fixed;     /* Keeps the element fixed on the screen */
    top: 140px;              /* Aligns the element to the top of the screen */
    right: 50px;         /* Adjust the right position as needed */
    max-width: 100%;     /* Ensures the element width doesn't exceed area */
    z-index: 9999;       /* Ensures the element is on top of other content */
    max-height: calc(100vh - 280px); /* Sets the maximum height to 100% of viewport height minus 140px */
    overflow: auto;      /* Adds a scrollbar when the content overflows */
    overflow-x: hidden;  /* Hides horizontal scrollbar */
}
"""

        with main_window_container:
            with stylable_container(key="collections_container", css_styles=css_style):
                if "rag_ai" in st.session_state:
                    st.caption("Selected document collection:")
                    # This is a hack, but it works
                    col1, col2 = st.columns([0.80, 0.2])
                    ui_shared.create_collection_selectbox(
                        col1, ai=st.session_state["rag_ai"]
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
                            ui_shared.create_collection(
                                st.session_state["new_collection_name"]
                            )
                            st.experimental_rerun()

                    if "rag_ai" in st.session_state:
                        collection_id = ui_shared.get_selected_collection_id()
                        if collection_id != -1:
                            loaded_docs_delimited = None
                            if collection_id != -1:
                                st.session_state.rag_ai.interaction_manager.collection_id = (
                                    collection_id
                                )

                                loaded_docs = (
                                    st.session_state.rag_ai.interaction_manager.get_loaded_documents_for_display()
                                )

                                loaded_docs_delimited = (
                                    st.session_state.rag_ai.interaction_manager.get_loaded_documents_delimited()
                                )

                                with st.expander(
                                    label=f"({len(loaded_docs)}) documents in {ui_shared.get_selected_collection_name()}",
                                    expanded=False,
                                ):
                                    for doc in loaded_docs:
                                        st.write(doc)

                            st.markdown("### RAG Options")

                            with st.expander("Search"):  # , expanded=expanded):
                                st.radio(
                                    "Text search method",
                                    ["Similarity", "Keyword"],
                                    key="search_method",
                                    index=0,
                                )
                                st.number_input(
                                    "Top K (number of document chunks to use in searches)",
                                    key="search_top_k",
                                    value=5,
                                )
                                st.selectbox(
                                    "Summarization strategy",
                                    ["map_reduce", "refine"],
                                    key="summarization_strategy",
                                )
                                st.toggle(
                                    "Re-run user query after search / summarization",
                                    help="This will re-run the user query after the search and summarization is complete.  This can sometimes yield better results, but it can also hide data you may find relevant.",
                                    value=False,
                                    key="re_run_user_query",
                                )

                            with st.expander("Spreadsheets"):
                                st.toggle(
                                    "Use Pandas for Spreadsheets",
                                    key="use_pandas",
                                    value=True,
                                )

                            with st.expander("General"):
                                options = []
                                if loaded_docs_delimited:
                                    options = [d for d in loaded_docs_delimited]

                                options.insert(0, "0:---")

                                st.selectbox(
                                    "Override automatic document selection:",
                                    options=options,
                                    key="override_file",
                                    format_func=lambda x: x.split(":")[1],
                                )
                                st.number_input(
                                    "Timeout (seconds)", key="agent_timeout", value=120
                                )

                            tools = st.session_state.rag_ai.get_all_tools()

                            def toggle_tool(tool_name):
                                st.session_state.rag_ai.toggle_tool(tool_name)

                            with st.expander("Available RAG Tools"):
                                for tool in tools:
                                    st.toggle(
                                        tool["name"],
                                        key=tool["name"],
                                        help=tool["about"],
                                        value=tool["enabled"],
                                        on_change=toggle_tool,
                                        kwargs={"tool_name": tool["name"]},
                                    )
                        else:
                            st.warning("No collection selected")

            st.write("")
            st.write("")
            st.write("")
            st.write("")
            st.write("")
            st.write("")

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

    def show_old_messages(self, rag_ai_instance):
        self.refresh_messages_session_state(rag_ai_instance)

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
                    st.session_state[
                        f"confirm_conversation_item_delete_{message['id']}"
                    ]
                    == False
                ):
                            
                    col3.button(
                        "🗑️",
                        help="Delete this conversation entry?",
                        on_click=ui_shared.set_confirm_conversation_item_delete,
                        kwargs={"val": True, "id": message["id"]},
                        key=str(uuid.uuid4()),
                    )
                else:
                    col2.button(
                        "✅",
                        help="Click to confirm delete",
                        key=str(uuid.uuid4()),
                        on_click=ui_shared.delete_conversation_item,
                        kwargs={"id": message["id"]},
                    )
                    
                    col3.button(
                        "❌",
                        help="Click to cancel delete",
                        on_click=ui_shared.set_confirm_conversation_item_delete,
                        kwargs={"val": False, "id": message["id"]},
                        key=str(uuid.uuid4()),
                    )

                col1.markdown(message["content"])

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
            st.write("")

        # Get user input (must be outside of the container)
        prompt = st.chat_input("Enter your message here", key="chat_input")

        if prompt:
            logging.debug(f"User input: {prompt}")

            with main_window_container.container():
                st.chat_message("user", avatar="👤").markdown(prompt)

                with st.chat_message("assistant", avatar="🤖"):
                    thought_container = st.container()
                    llm_container = st.container()
                    results_callback = ResultOnlyCallbackHandler()
                    callbacks = []
                    callbacks.append(results_callback)
                    callbacks.append(
                        StreamlitCallbackHandler(
                            parent_container=thought_container,
                            expand_new_thoughts=True,
                            collapse_completed_thoughts=True,
                        )
                    )

                    collection_id = ui_shared.get_selected_collection_id()

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
                        else 120,
                        "summarization_strategy": st.session_state[
                            "summarization_strategy"
                        ]
                        if "summarization_strategy" in st.session_state
                        else "map_reduce",
                        "re_run_user_query": st.session_state["re_run_user_query"]
                        if "re_run_user_query" in st.session_state
                        else True,
                    }
                    logging.debug(f"kwargs: {kwargs}")

                    try:
                        result = rag_ai_instance.query(
                            query=prompt,
                            collection_id=collection_id
                            if collection_id != -1
                            else None,
                            agent_callbacks=callbacks,
                            kwargs=kwargs,
                        )
                    except Exception as e:
                        logging.error(f"Error querying AI: {e}")
                        result = (
                            "Error querying AI, please try again (and see the logs)."
                        )

                    logging.debug(f"Result: {result}")

                    llm_container.markdown(result)

                    # TODO: Put this thought container text into the DB (it provides great context!)
                    # logging.debug(
                    #     f"TODO: Put this thought container text into the DB (it provides great context!): {results_callback.response}"
                    # )


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOGGING_LEVEL", "INFO"))

    try:
        logging.debug("Starting Jarvis")
        rag_ui = RagUI()

        # Always comes first!
        logging.debug("Loading configuration")
        rag_ui.load_configuration()

        logging.debug("Setting page config")
        rag_ui.set_page_config()

        # Get the user from the environment variables
        user_email = os.environ.get("USER_EMAIL", None)
        rag_ui.user_email = user_email
        logging.debug(f"User email: {user_email}")

        if not user_email:
            raise ValueError("USER_EMAIL environment variable not set")

        logging.debug("Ensuring user exists")
        if ui_shared.ensure_user(user_email):
            logging.debug("User exists")
            ui_shared.set_user_id_from_email(user_email)
            ui_shared.ensure_interaction()

            conversations, files_and_settings = st.sidebar.tabs(
                ["Conversations", "Files & Settings"]
            )

            ui_shared.load_conversation_selectbox(rag_ui.load_ai, conversations)
            # Set up columns for chat and collections
            col1, col2 = st.columns([0.65, 0.35])

            rag_ui.load_ai()
            ui_shared.setup_new_chat_button(conversations)
            rag_ui.create_collections_container(col2)

            ui_shared.select_documents(
                ai=st.session_state["rag_ai"], tab=files_and_settings
            )

            rag_ui.handle_chat(col1)

            ui_shared.show_version()
    except Exception as e:
        # This should only be catching a StopException thrown by streamlit, yet I cannot find it for the fucking life of me.
        # And after wasting 20 minutes of my life on this, I am done.

        logging.error(f"Caught a general exception: {e}")
        st.error(f"Caught a general exception: {e}")

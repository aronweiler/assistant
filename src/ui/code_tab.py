import datetime
import logging
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from src.ai.prompts.prompt_models.code_details_extraction import CodeDetailsExtractionOutput
from src.ai.rag_ai import RetrievalAugmentedGenerationAI
from src.db.models.code import Code
from src.db.models.conversations import Conversations
from src.tools.code.code_retriever_tool import CodeRetrieverTool
import src.ui.streamlit_shared as streamlit_shared


def get_available_code_repositories():
    # Time the operation:
    repos = Code().get_repositories()

    # Create a dictionary of repo id to repo address
    repos_list = [
        f"{repo.id}:{repo.code_repository_address.replace('https://', '').replace('http://', '')} ({repo.branch_name})"
        for repo in repos
    ]

    repos_list.insert(0, "-1:---")

    return repos_list


def create_code_collection_tab(ai, tab: DeltaGenerator):
    with tab:
        st.markdown("Select a repository")
        st.caption(
            "The code repository selected here determines which code is used by the AI."
        )

        col1, col2 = st.columns([0.80, 0.2])

        available_repos = get_available_code_repositories()
        selected_repo_index = 0
        # Find the index of the selected collection
        for i, repo in enumerate(available_repos):
            if int(repo.split(":")[0]) == int(
                ai.conversation_manager.get_conversation().last_selected_code_repo
            ):
                selected_repo_index = i
                break

        col1.selectbox(
            label="Active code repository",
            index=int(selected_repo_index),
            options=available_repos,
            key="active_code_repo",
            placeholder="Select a repository",
            label_visibility="collapsed",
            format_func=lambda x: x.split(":")[1],
            on_change=on_change_code_repo,
        )

        if col2.button("➕", help="Add a new code repository", key="show_add_code_repo"):
            st.session_state.adding_repo = True

        repo_id = streamlit_shared.get_selected_code_repo_id()

        if not st.session_state.get("adding_repo", False) and repo_id != -1:
            # Show the scan repo button
            scan_col_1, scan_col_2 = st.columns([0.6, 0.4])
            repo = Code().get_repository(repo_id)
            if repo:
                scan_col_1.markdown(f"Last scan: **{repo.last_scanned or 'Never'}**")
                scan_col_2.button(
                    "Scan repository",
                    help="Scan the code repository",
                    key="scan_repo",
                    on_click=scan_repo,
                    args=(
                        tab,
                        ai,
                    ),
                )

        elif st.session_state.get("adding_repo", False):
            col1.caption("Repository address:")
            col1.text_input(
                "Repository address",
                label_visibility="collapsed",
                key="new_repo_address",
            )

            # Create the refresh button to refresh the branches from the repo
            col2.button("🔄", help="Refresh branches", key="refresh_branches")

            show_branches(tab=tab)


def add_repository():
    code = Code()

    code.add_repository(
        st.session_state.get("new_repo_address", ""),
        st.session_state.get("new_branch_name", ""),
    )

    # Reset the adding repo state
    st.session_state.adding_repo = False


def show_branches(tab: DeltaGenerator):
    """Refreshes the branches for the specified repo address"""
    repo_address = st.session_state.get("new_repo_address", "")
    adding_repo = st.session_state.get("adding_repo", False)

    if adding_repo:
        with tab:
            if repo_address != "":
                try:
                    retriever = CodeRetrieverTool()
                    branches = retriever.get_branches(repo_address)
                except Exception as e:
                    st.error(f"Could not retrieve branches: {e}")
                    return

                if branches:
                    st.selectbox("Branch name", options=branches, key="new_branch_name")

                    col1, col2 = st.columns(2)
                    col1.button(
                        "Add Repository",
                        type="primary",
                        on_click=add_repository,
                    )

                    col2.button(
                        "Cancel",
                        type="secondary",
                        on_click=lambda: st.session_state.update(
                            {"adding_repo": False}
                        ),
                    )
                else:
                    st.error("Could not find any branches for this repo")
            else:
                st.info("Please enter a repo address")


def on_change_code_repo():
    """Called when the code repo is changed"""
    # Set the last active code repo for this conversation (conversation)
    code_repo_id = streamlit_shared.get_selected_code_repo_id()

    st.session_state.rag_ai.conversation_manager.set_selected_repository(
        Code().get_repository(code_repo_id)
    )


def scan_repo(tab: DeltaGenerator, ai: RetrievalAugmentedGenerationAI):
    """Scans the selected repo"""
    code_repo_id = streamlit_shared.get_selected_code_repo_id()
    code_repo = Code().get_repository(code_repo_id)
    retriever = CodeRetrieverTool()

    files = retriever.scan_repo(
        code_repo.code_repository_address, code_repo.branch_name
    )

    # Unlink all of the previously scanned files, if any, from this repo
    Code().unlink_code_files(code_repo_id)

    with tab:
        st.info(f"Found {len(files)} files")

        unprocessed_files = []

        if len(files) > 0:
            progress_bar = st.progress(0)
            progress_text = st.empty()

            for i, file in enumerate(files):
                progress_text.text(f"Processing {file.path}")
                if not process_code_file(
                    file=file,
                    ai=ai,
                    repo_address=code_repo.code_repository_address,
                    branch_name=code_repo.branch_name,
                    code_repo_id=code_repo_id,
                ):
                    unprocessed_files.append(file.path)

                progress_bar.progress((i + 1) / len(files))

            progress_bar.empty()

            Code().update_last_scanned(code_repo_id, datetime.datetime.now())

            st.success(f"Done scanning {len(files)} files!")

            if len(unprocessed_files) > 0:
                st.warning(f"Could not process {len(unprocessed_files)} files:")
                st.write(unprocessed_files)


def process_code_file(
    file,
    ai: RetrievalAugmentedGenerationAI,
    repo_address: str,
    branch_name: str,
    code_repo_id: int,
):
    """Processes the code file"""
    code_helper = Code()

    # Skip the file if the same file (sha) has already been processed
    existing_code_file_id = code_helper.get_code_file_id(
        code_file_name=file.path, file_sha=file.sha
    )
    if existing_code_file_id:
        # Link the code file with the code repo
        code_helper.link_code_file_to_repo(
            code_file_id=existing_code_file_id, code_repo_id=code_repo_id
        )

        logging.info(
            f"The file `{file.path}` has already been processed- linking it to this repo."
        )
        return True
    try:
        # Retrieve the code from the file
        code_data = CodeRetrieverTool().get_code_from_repo_and_branch(
            file.path, repo_address, branch_name
        )

        code = code_data["file_content"]

        if code.strip() != "":
            # Generate the keywords from the code
            keywords_and_descriptions = (
                ai.generate_keywords_and_descriptions_from_code_file(code)
            )
            
        else:
            keywords_and_descriptions = None

        # Store the code and keywords in the database

        code_helper.add_update_code(
            file_name=file.path,
            file_sha=file.sha,
            file_content=code,
            keywords_and_descriptions=keywords_and_descriptions,
            repository_id=code_repo_id,
            file_summary=keywords_and_descriptions.summary if keywords_and_descriptions else "",
        )

        return True
    except Exception as e:
        logging.error(f"Could not process file {file.path}: {e}")
        return False

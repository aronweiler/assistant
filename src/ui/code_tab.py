import datetime
import logging
import os
import shutil
import streamlit as st
from streamlit.delta_generator import DeltaGenerator
from src.ai.rag_ai import RetrievalAugmentedGenerationAI
from src.db.models.code import Code
from src.db.models.conversations import Conversations
from src.db.models.user_settings import UserSettings
from src.documents.codesplitter.splitter.dependency_analyzer import DependencyAnalyzer
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

        if col2.button(
            "➕", help="Add a new code repository", key="show_add_code_repo"
        ):
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
                    retriever = CodeRetrieverTool(
                        conversation_manager=st.session_state.rag_ai.conversation_manager,
                        configuration=None,
                    )
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
    retriever = CodeRetrieverTool(
        conversation_manager=st.session_state.rag_ai.conversation_manager,
        configuration=None,
    )

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

            # Create a unique temp directory to store the files
            temp_dir = f"/tmp/code/{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            files = filter_and_save_files(
                files=files,
                temp_dir=temp_dir,
                code_repo_id=code_repo_id,
                repo_address=code_repo.code_repository_address,
                branch_name=code_repo.branch_name,
                progress_bar=progress_bar,
                progress_text=progress_text,
            )

            # Reset the progress bar
            progress_bar.progress(0)

            for i, file in enumerate(files):
                progress_text.text(f"Processing changed file:\n'{file.path}'")
                if not process_code_file(
                    temp_dir=temp_dir,
                    file=file,
                    ai=ai,
                    code_repo_id=code_repo_id,
                ):
                    unprocessed_files.append(file.path)

                progress_bar.progress((i + 1) / len(files))

            try:
                # if the temp directory exists, remove it
                if os.path.exists(temp_dir):
                    # Remove the temp directory, including all files and subdirectories
                    shutil.rmtree(temp_dir)
            except Exception as e:
                logging.error(f"Could not remove temp directory {temp_dir}: {e}")

            process_dependencies(
                repo_id=code_repo_id,
                progress_bar=progress_bar,
                progress_text=progress_text,
            )

            progress_bar.empty()

            Code().update_last_scanned(code_repo_id, datetime.datetime.now())

            st.success(f"Done processing {len(files)} new or changed files")

            if len(unprocessed_files) > 0:
                st.warning(f"Could not process {len(unprocessed_files)} files:")
                st.write(unprocessed_files)


def filter_and_save_files(
    files,
    temp_dir,
    code_repo_id,
    repo_address,
    branch_name,
    progress_bar,
    progress_text,
):
    import os
    from src.db.models.code import Code

    code_helper = Code()
    count = 0

    files_to_process = []

    for i, file in enumerate(files):
        progress_text.text(f"Inspecting:\n{file.path}")
        progress_bar.progress((i + 1) / len(files))

        # Skip the file if the same file (sha) has already been processed
        existing_code_file_id = code_helper.get_code_file_id(
            code_file_name=file.path, file_sha=file.sha
        )
        if existing_code_file_id:
            # Skip saving the file, but link the code file with the code repo
            code_helper.link_code_file_to_repo(
                code_file_id=existing_code_file_id, code_repo_id=code_repo_id
            )

            progress_text.text(f"{file.path} unchanged")
            logging.info(
                f"The file `{file.path}` has already been processed- linking it to this repo."
            )

        else:
            # File does not exist, so prepare to write it out
            retriever = CodeRetrieverTool(
                conversation_manager=st.session_state.rag_ai.conversation_manager,
                configuration=None,
            )

            # Retrieve the code from the repo
            code_data = retriever.get_code_from_repo_and_branch(
                file.path, repo_address, branch_name
            )

            code = code_data["file_content"]

            file_path = os.path.join(temp_dir, file.path)
            # replace any backslashes with forward slashes
            file_path = file_path.replace("\\", "/")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Create the file at the file_path location
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            files_to_process.append(file)

            count += 1

    logging.info(
        f"{count} files were different/new, and have been saved to {temp_dir}."
    )

    return files_to_process


def process_code_file(
    temp_dir: str,
    file,
    ai: RetrievalAugmentedGenerationAI,
    code_repo_id: int,
):
    """Processes the code file"""
    code_helper = Code()

    try:
        file_path = os.path.join(temp_dir, file.path)

        # read the code in from the file
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        if code.strip() != "":
            # Generate the keywords and descriptions from the code, skipping empty files
            keywords_and_descriptions = (
                ai.generate_keywords_and_descriptions_from_code_file(code)
            )

        else:
            keywords_and_descriptions = None

        embedding_name = (
            UserSettings()
            .get_user_setting(
                user_id=st.session_state.rag_ai.conversation_manager.user_id,
                setting_name="repository_embedding_name",
                default_value="OpenAI: text-embedding-3-small",
            )
            .setting_value
        )

        # Store the code and keywords in the database
        code_file_id = code_helper.add_update_code(
            file_name=file.path,
            file_sha=file.sha,
            file_content=code,
            keywords_and_descriptions=keywords_and_descriptions,
            repository_id=code_repo_id,
            file_summary=(
                keywords_and_descriptions.summary if keywords_and_descriptions else ""
            ),
            embedding_name=embedding_name,
        )

        if not code_file_id:
            logging.error(
                f"Could not add code file {file.path} to the database. Skipping."
            )
            return False

        return True
    except Exception as e:
        logging.error(f"Could not process file {file.path}: {e}")
        return False


def process_dependencies(repo_id: int, progress_bar, progress_text):
    # This is a final step when ingesting a repo, where we process the dependencies of the files we've stored
    code_helper = Code()
    dependency_analyzer = DependencyAnalyzer()
    progress_text.text(f"Processing dependencies for repo")
    progress_bar.progress(0)

    # Write out the repo contents (from the database) to a temp directory
    repo_files = code_helper.get_code_files(repo_id)

    temp_dir = f"/tmp/code-deps/{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Make sure the temp directory exists and is empty

    for i, file in enumerate(repo_files):
        progress_text.text(
            f"Preparing to scan for dependencies:\n'{file.code_file_name}'"
        )
        # Get the file content
        file_content = file.code_file_content
        file_path = f"{temp_dir}/{file.code_file_name}"

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write the file content to a temp directory
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)

        progress_bar.progress((i + 1) / len(repo_files))

    progress_bar.progress(0)

    # Once all of the files are written, process the dependencies
    for i, file in enumerate(repo_files):
        progress_text.text(f"Scanning for dependencies:\n'{file.code_file_name}'")
        # Remove any existing dependencies for this file
        code_helper.delete_code_file_dependencies(file.id)

        # Process the dependencies
        dependencies = dependency_analyzer.process_code_file(
            f"{temp_dir}/{file.code_file_name}", temp_dir
        )

        if dependencies:
            # Add the dependencies to the database
            for dependency in dependencies["dependencies"]:
                code_helper.add_code_file_dependency(
                    code_file_id=file.id,
                    dependency_name=dependency,
                )

        progress_bar.progress((i + 1) / len(repo_files))

    # Remove the temp directory
    try:
        # if the temp directory exists, remove it
        if os.path.exists(temp_dir):
            # Remove the temp directory, including all files and subdirectories
            shutil.rmtree(temp_dir)
    except Exception as e:
        logging.error(f"Could not remove temp directory {temp_dir}: {e}")

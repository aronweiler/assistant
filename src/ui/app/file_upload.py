import streamlit as st
import os
import uuid

from utilities import calculate_progress
from src.workers.document_processing.app import document_ingestion_tasks


def ingest_files(
    uploaded_files,
    active_collection_id,
    status,
    overwrite_existing_files,
    split_documents,
    create_summary_and_chunk_questions,
    summarize_document,
    chunk_size,
    chunk_overlap,
    ai=None,
):
    """Ingests the uploaded files into the specified collection"""
    # Write out the files to the shared volume in a unique directory for this batch
    ingest_progress_bar = st.progress(text="Uploading files...", value=0)
    uploaded_file_paths, root_temp_dir = upload_files(
        uploaded_files, status, ingest_progress_bar
    )

    for file_path in uploaded_file_paths:
        # Hand off to Celery for processing each file separately
        document_ingestion_tasks.process_document_task.delay(
            active_collection_id=active_collection_id,
            overwrite_existing_files=overwrite_existing_files,
            split_documents=split_documents,
            create_summary_and_chunk_questions=create_summary_and_chunk_questions,
            summarize_document=summarize_document,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            user_id=st.session_state.user_id,
            file_path=file_path,
        )

    status.update(
        label=f"✅ Ingestion queued",
        state="complete",
    )
    ingest_progress_bar.empty()


def upload_files(uploaded_files, status, ingest_progress_bar, root_dir="/app/shared"):
    # Create a path by combining the root directory with a unique identifier

    root_temp_dir = root_dir + "/document_uploads/" + str(uuid.uuid4())

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

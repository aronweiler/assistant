import asyncio
import logging
import os
import sys

from celery import current_task

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../"))

from src.workers.document_processing.app.celery_worker import celery_app


@celery_app.task(name="process_document_task")  # bind=True
def process_document_task(
    active_collection_id: int,
    overwrite_existing_files: bool,
    split_documents: bool,
    create_summary_and_chunk_questions: bool,
    summarize_document: bool,
    chunk_size: int,
    chunk_overlap: int,
    user_id: int,
    file_path: str,
):
    """Process (split, vectorize, etc.) a single document and store it in the database"""
    logging.info(f"Worker processing document '{file_path}'...")
    current_task.update_state(
        state="STARTED", meta={"status": f"Worker processing document '{file_path}'..."}
    )

    # Imports are within the function because we don't want to load them unless we're using them
    from src.shared.database.models.documents import Documents
    from src.shared.database.models.domain.file_model import FileModel
    from src.shared.utilities.hash_utilities import calculate_sha256
    from src.workers.document_processing.app.document_loader import (
        file_needs_converting,
        convert_file_to_pdf,
        load_and_split_document,
    )

    documents_helper = Documents()

    original_file_name = os.path.basename(file_path)

    current_task.update_state(
        state="PROGRESS", meta={"status": "Checking for existing files..."}
    )
    # Do we already have this file in the database?
    existing_file = documents_helper.get_file_by_name(
        original_file_name, active_collection_id
    )

    if existing_file:
        if not overwrite_existing_files:
            logging.warning(
                f"File '{original_file_name}' already exists, and overwrite is not enabled"
            )
            current_task.update_state(
                state="FAILURE",
                meta={
                    "status": f"File '{original_file_name}' already exists, and overwrite is not enabled"
                },
            )

            return

        current_task.update_state(
            state="PROGRESS", meta={"status": "Overwriting existing file..."}
        )
        # Delete the old file and its chunks
        documents_helper.delete_document_chunks_by_file_id(existing_file.id)
        documents_helper.delete_file(existing_file.id)

    # Does the file need to be converted to a different format?
    if file_needs_converting(file_path):
        logging.info(f"Converting file '{file_path}' to PDF...")
        current_task.update_state(
            state="PROGRESS",
            meta={"status": f"Converting file '{file_path}' to PDF..."},
        )
        # Convert the file, and reset the file_path
        file_path = convert_file_to_pdf(file_path)

    # Load and split the document
    current_task.update_state(
        state="PROGRESS",
        meta={"status": f"Loading and splitting '{file_path}'..."},
    )
    documents = load_and_split_document(
        target_file=file_path,
        split_document=split_documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    logging.info(
        f"After loading and splitting, we are processing {len(documents)} documents..."
    )

    # Get the full file data for the database
    with open(file_path, "rb") as file:
        file_data = file.read()

    # Get the hash of the file
    file_hash = calculate_sha256(file_path)

    logging.info(f"Storing full document '{original_file_name}'...")
    current_task.update_state(
        state="PROGRESS",
        meta={"status": f"Storing full document '{original_file_name}'..."},
    )

    file_classification = documents[0].metadata["classification"]

    file_model = documents_helper.create_file(
        FileModel(
            user_id=user_id,
            collection_id=active_collection_id,
            file_name=original_file_name,
            file_hash=file_hash,
            file_classification=file_classification,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ),
        file_data,  # Binary file data for later retrieval
    )

    # TODO: Iterate through the document chunks and store them
   

# def ingest_files(
#     uploaded_files,
#     active_collection_id,
#     status,
#     overwrite_existing_files,
#     split_documents,
#     create_chunk_questions,
#     summarize_chunks,
#     summarize_document,
#     chunk_size,
#     chunk_overlap,
#     ai=None,
# ):
#     """Ingests the uploaded files into the specified collection"""

#     documents_helper = Documents()
#     document_loader = DocumentLoader()
#     documents = None

#     if not active_collection_id:
#         st.error("No collection selected")
#         return

#     if not uploaded_files:
#         st.error("No files selected")
#         return

#     status.update(
#         label=f"Ingesting files and adding to '{get_selected_collection_name()}'",
#         state="running",
#     )

#     ingest_progress_bar = st.progress(text="Uploading files...", value=0)

#     # First upload the files to our temp directory
#     uploaded_file_paths, root_temp_dir = upload_files(
#         uploaded_files, status, ingest_progress_bar
#     )

#     with status.container():
#         with st.empty():
#             st.info(f"Processing {len(uploaded_file_paths)} files...")
#             logging.info(f"Processing {len(uploaded_file_paths)} files...")
#             # First see if there are any files we can't load
#             files = []
#             for uploaded_file_path in uploaded_file_paths:
#                 ingest_progress_bar.progress(
#                     calculate_progress(
#                         len(uploaded_file_paths),
#                         uploaded_file_paths.index(uploaded_file_path) + 1,
#                     ),
#                     text=f"Uploading file {uploaded_file_paths.index(uploaded_file_path) + 1} of {len(uploaded_file_paths)}",
#                 )

#                 # Get the file name
#                 file_name = (
#                     uploaded_file_path.replace(root_temp_dir, "").strip("/").strip("\\")
#                 )

#                 st.info(f"Verifying {uploaded_file_path}...")
#                 logging.info(f"Verifying {uploaded_file_path}...")

#                 # See if it exists in this collection
#                 existing_file = documents_helper.get_file_by_name(
#                     file_name, active_collection_id
#                 )

#                 if existing_file and not overwrite_existing_files:
#                     # See if the hash on this file matches the one we have stored
#                     if existing_file.file_hash == calculate_sha256(uploaded_file_path):
#                         # It matches, so split the file using the existing document chunks settings
#                         st.info(
#                             f"File '{file_name}' already exists, and the hash matches, so we're checking to see if it's a RESUME op..."
#                         )
#                         logging.info(
#                             f"File '{file_name}' already exists, and the hash matches, so we're checking to see if it's a RESUME op..."
#                         )

#                         if (
#                             existing_file.file_classification
#                             != st.session_state.ingestion_settings.file_type
#                         ):
#                             st.error(
#                                 f"File '{file_name}' already exists, and the hash matches, but the file type has changed.  Please set the overwrite option and try again."
#                             )
#                             logging.error(
#                                 f"File '{file_name}' already exists, and the hash matches, but the file type has changed.  Please set the overwrite option and try again."
#                             )

#                         # TODO: Fix all of this- it's a total inefficient mess, the document ingestion needs to be completely re-written

#                         # Split the document
#                         documents = asyncio.run(
#                             document_loader.load_and_split_documents(
#                                 document_directory=root_temp_dir,
#                                 split_documents=split_documents,
#                                 is_code=existing_file.file_classification == "Code",
#                                 chunk_size=existing_file.chunk_size,
#                                 chunk_overlap=existing_file.chunk_overlap,
#                             )
#                         )

#                         # Get the documents that match this file name
#                         matching_documents = [
#                             d
#                             for d in documents
#                             if d.metadata["filename"]
#                             .replace(root_temp_dir, "")
#                             .strip("/")
#                             == file_name
#                         ]

#                         if (
#                             len(matching_documents) == existing_file.document_count
#                             or existing_file.document_count == 0
#                         ):
#                             files.append(existing_file)
#                         else:
#                             st.error(
#                                 f"File '{file_name}' already exists, and the hash matches, but the number of documents in the file has changed.  Please delete the file and try again."
#                             )
#                             logging.error(
#                                 f"File '{file_name}' already exists, and the hash matches, but the number of documents in the file has changed.  Please delete the file and try again."
#                             )

#                     st.warning(
#                         f"File '{file_name}' already exists, and overwrite is not enabled"
#                     )
#                     logging.warning(
#                         f"File '{file_name}' already exists, and overwrite is not enabled"
#                     )
#                     logging.debug(f"Deleting temp file: {uploaded_file_path}")
#                     os.remove(uploaded_file_path)

#                     continue

#                 elif not existing_file or (existing_file and overwrite_existing_files):
#                     # Delete the document chunks
#                     if existing_file:
#                         documents_helper.delete_document_chunks_by_file_id(
#                             existing_file.id
#                         )

#                         # Delete the existing file
#                         documents_helper.delete_file(existing_file.id)

#                     # File does not exist (or was deleted)
#                     # Read the file
#                     with open(uploaded_file_path, "rb") as file:
#                         file_data = file.read()

#                     # Start off with the default file classification
#                     file_classification = st.session_state.ingestion_settings.file_type

#                     # Override the classification if necessary
#                     # Get the file extension
#                     file_extension = os.path.splitext(file_name)[1]
#                     # Check to see if it's an image
#                     if file_extension in IMAGE_TYPES:
#                         # It's an image, reclassify it
#                         file_classification = "Image"

#                     # Create the file
#                     logging.info(f"Creating file '{file_name}'...")
#                     file_model = documents_helper.create_file(
#                         FileModel(
#                             user_id=st.session_state.user_id,
#                             collection_id=active_collection_id,
#                             file_name=file_name,
#                             file_hash=calculate_sha256(uploaded_file_path),
#                             file_classification=file_classification,
#                             chunk_size=chunk_size,
#                             chunk_overlap=chunk_overlap,
#                         ),
#                         file_data,
#                     )
#                     files.append(file_model)

#             if not files or len(files) == 0:
#                 st.warning("Nothing to split... bye!")
#                 logging.warning("No files to ingest")
#                 ingest_progress_bar.empty()
#                 status.update(
#                     label=f"⚠️ Ingestion complete (with warnings)",
#                     state="complete",
#                 )
#                 return

#             st.info("Splitting documents...")
#             logging.info("Splitting documents...")

#             is_code = st.session_state.ingestion_settings.file_type == "Code"

#             # Pass the root temp dir to the ingestion function
#             # if we've already split the docs, don't do it again
#             if not documents:
#                 documents = asyncio.run(
#                     document_loader.load_and_split_documents(
#                         document_directory=root_temp_dir,
#                         split_documents=split_documents,
#                         is_code=is_code,
#                         chunk_size=chunk_size,
#                         chunk_overlap=chunk_overlap,
#                     )
#                 )

#             if documents == None:
#                 st.warning(
#                     f"No documents could be extracted from these files.  Possible images detected..."
#                 )
#                 st.success(f"Completed ingesting {len(files)} files")
#                 status.update(
#                     label=f"✅ Ingestion complete",
#                     state="complete",
#                 )
#                 logging.info(
#                     f"No documents could be extracted from these files.  Possible images detected..."
#                 )
#                 return

#             save_split_documents(
#                 active_collection_id,
#                 status,
#                 create_chunk_questions,
#                 summarize_chunks,
#                 summarize_document,
#                 ai,
#                 documents_helper,
#                 ingest_progress_bar,
#                 root_temp_dir,
#                 files,
#                 documents,
#             )

#     # Done!
#     st.balloons()

import streamlit as st
from src.db.models.documents import Documents

# Placeholder for the Documents class instantiation
documents = Documents()


def delete_associated_files(collection_id):
    # Placeholder function to delete associated files of a collection
    files_in_collection = documents.get_files_in_collection(collection_id)
    for file in files_in_collection:
        documents.delete_document_chunks_by_file_id(file.id)
        documents.delete_file(file.id)


def get_empty_collections():
    # Placeholder function to return collections without associated files
    all_collections = documents.get_collections()
    empty_collections = [
        collection
        for collection in all_collections
        if not documents.get_files_in_collection(collection.id)
    ]
    return empty_collections


def main():
    st.title("Document Management")

    # Select a file
    all_files = documents.get_all_files()
    file_options = [(f"{file.file_name} (ID: {file.id})", file) for file in all_files]
    file_option_names, file_objects = zip(*file_options) if all_files else ([], [])
    selected_file_name = st.selectbox("Select a File", options=file_option_names)

    selected_file = next(
        (
            file
            for file in file_objects
            if f"{file.file_name} (ID: {file.id})" == selected_file_name
        ),
        None,
    )

    if selected_file:
        # View file summary and classification in an expander
        with st.expander(f"File Details ({selected_file.file_classification}, has summary: {selected_file.file_summary != None})"):
            st.write(f"Summary: {selected_file.file_summary}")
            st.write(f"Classification: {selected_file.file_classification}")

        # Delete the selected file and its associated document chunks
        if st.button(f"Delete File (ID: {selected_file.id})"):
            try:
                documents.delete_document_chunks_by_file_id(selected_file.id)
                documents.delete_file(selected_file.id)
                st.success(
                    f"File '{selected_file.file_name}' and its associated documents have been deleted."
                )
            except Exception as e:
                st.error(f"An error occurred while deleting the file: {e}")

        # Change a file's collection
        all_collections = documents.get_collections()
        collection_options = [
            (collection.collection_name, collection) for collection in all_collections
        ]
        collection_option_names, collection_objects = (
            zip(*collection_options) if all_collections else ([], [])
        )

        target_collection_name = st.selectbox(
            "Select Target Collection", options=collection_option_names
        )

        target_collection = next(
            (
                collection
                for collection in collection_objects
                if collection.collection_name == target_collection_name
            ),
            None,
        )

        if target_collection and st.button(
            f"Change Collection of File (ID: {selected_file.id})"
        ):
            try:
                documents.set_collection_id_for_file(
                    selected_file.id, target_collection.id
                )
                documents.set_collection_id_for_document_chunks(
                    selected_file.id, target_collection.id
                )
                st.success(
                    f"File '{selected_file.file_name}' has been moved to the collection '{target_collection.collection_name}'."
                )
            except Exception as e:
                st.error(f"An error occurred while changing the file's collection: {e}")

    # Delete a selected collection and optionally its associated files

    st.divider()

    with st.form(key="delete_collection_form"):
        selected_collection_name_to_delete = st.selectbox(
            "Select a Collection to Delete",
            options=[col.collection_name for col in (all_collections)],
        )

        delete_files_toggle = st.toggle("Delete Associated Files?", help="Turn this on to enable deleting collections with files.", value=False)

        submit_button = st.form_submit_button(label="Delete Collection")

    if submit_button:
        try:
            selected_collection_to_delete = next(
                (
                    col
                    for col in all_collections
                    if col.collection_name == selected_collection_name_to_delete
                ),
                None,
            )

            if delete_files_toggle:
                delete_associated_files(selected_collection_to_delete.id)

            documents.delete_collection(selected_collection_to_delete.id)

            message_suffix = (
                " and its associated files have been deleted."
                if delete_files_toggle
                else " has been deleted."
            )
            st.success(
                f"Collection '{selected_collection_to_delete.collection_name}'{message_suffix}"
            )

        except Exception as e:
            st.error(f"An error occurred while deleting the collection: {e}")


if __name__ == "__main__":
    main()

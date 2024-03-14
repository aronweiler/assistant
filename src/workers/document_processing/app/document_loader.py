import logging
import os
import sys
from subprocess import Popen
from typing import List
import asyncio
import tiktoken

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


# TODO: Add loaders for PPT, and other document types
from langchain_community.document_loaders import (
    CSVLoader,
    TextLoader,
    Docx2txtLoader,
    BSHTMLLoader,
    PDFPlumberLoader,
    UnstructuredExcelLoader,
)

from shared.utilities.token_helper import num_tokens_from_string

SUPPORTED_DOCUMENT_TYPES = {
    ".txt": TextLoader,
    ".pdf": PDFPlumberLoader,
    ".csv": CSVLoader,
    ".ods": UnstructuredExcelLoader,
    ".xls": UnstructuredExcelLoader,
    ".xlsx": UnstructuredExcelLoader,
    ".html": BSHTMLLoader,
    ".htm": BSHTMLLoader,
}

DOCUMENT_CLASSIFICATIONS = {
    ".txt": "Document",
    ".pdf": "Document",
    ".csv": "Spreadsheet",
    ".xls": "Spreadsheet",
    ".xlsx": "Spreadsheet",
    ".ods": "Spreadsheet",
    # ".html": "Webpage",
}

# These need to be converted to PDF before being loaded
WORD_DOC_TYPES = {".doc": Docx2txtLoader, ".docx": Docx2txtLoader}

EXCEL_DOC_TYPES = {
    ".xls": UnstructuredExcelLoader,
    ".xlsx": UnstructuredExcelLoader,
    ".ods": UnstructuredExcelLoader,
}

# Default LibreOffice installation location (Linux)
LIBRE_OFFICE_DEFAULT = "/usr/bin/soffice"


def file_needs_converting(file_path: str) -> bool:
    file_extension = os.path.splitext(file_path)[1]
    return file_extension in WORD_DOC_TYPES


def get_libre_office_path() -> str:
    if "LIBRE_OFFICE_PATH" in os.environ:
        return os.environ["LIBRE_OFFICE_PATH"]
    elif os.path.exists(LIBRE_OFFICE_DEFAULT):
        return LIBRE_OFFICE_DEFAULT
    else:
        raise ValueError(
            f"Could not find LibreOffice installation. Please set the LIBRE_OFFICE_PATH environment variable to the installation path."
        )


def convert_file_to_pdf(file_path: str) -> str:
    out_folder = os.path.dirname(file_path)
    p = Popen(
        [
            get_libre_office_path(),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            out_folder,
            os.path.abspath(file_path),
        ],
    )
    logging.debug([get_libre_office_path(), "--convert-to", "pdf", file_path])

    p.communicate()

    return os.path.splitext(file_path)[0] + ".pdf"


def load_single_document(file_path: str) -> List[Document]:
    file_extension = os.path.splitext(file_path)[1]

    loader_class = SUPPORTED_DOCUMENT_TYPES.get(file_extension.lower())

    if loader_class:
        # This is where I would look to handle special cases for different file types
        documents = None
        if loader_class is UnstructuredExcelLoader:
            # Special case for excel files
            return []
        else:
            # No special case
            loader = loader_class(file_path)

        try:
            if not documents:
                # If we haven't loaded the documents yet, load them
                documents = loader.load()

            for doc in documents:
                # Get the file path without the directory
                doc.metadata["filename"] = os.path.basename(file_path)
                doc.metadata.setdefault("page", "N/A")
                doc.metadata.setdefault(
                    "classification",
                    DOCUMENT_CLASSIFICATIONS.get(file_extension.lower(), "Document"),
                )
            return documents
        except Exception as e:
            err = f"Could not load {file_path}, {e}"
            logging.error(err)
            raise ValueError(err)
    else:
        logging.error(f"Unsupported file type: '{file_extension}', {file_path}")


def get_documents_from_file(target_file: str) -> List[Document]:
    if os.path.splitext(target_file)[1] not in SUPPORTED_DOCUMENT_TYPES:
        raise ValueError(f"Unsupported file type: {target_file}")

    documents = load_single_document(target_file)
    logging.info(f"Loaded {len(documents)} documents from {target_file}")
    return documents


def load_and_split_document(
    target_file: str,
    split_document: bool,
    chunk_size: int,
    chunk_overlap: int,
) -> List[Document]:
    if not os.path.isfile(target_file):
        raise ValueError(f"target_file must be a file: {target_file}")

    documents = get_documents_from_file(target_file)

    if documents and split_document:        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=num_tokens_from_string,
        )
        texts = text_splitter.split_documents(documents)
        logging.info(
            f"Split into {len(texts)} chunks of text (chunk_size: {chunk_size}, chunk_overlap: {chunk_overlap})"
        )
    else:
        logging.info(f"Splitting is disabled, returning full documents")
        texts = documents

    logging.info(
        f"Loaded {len(documents)} pages split into {len(texts)} chunks from {target_file}"
    )

    return texts

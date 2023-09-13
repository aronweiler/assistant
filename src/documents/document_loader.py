import logging
import os
import sys
from subprocess import Popen
from typing import List

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Custom loaders
from src.documents.code_loader import CodeLoader

# TODO: Add loaders for PPT, and other document types
from langchain.document_loaders import CSVLoader, TextLoader, Docx2txtLoader, BSHTMLLoader, PDFPlumberLoader, UnstructuredExcelLoader

from src.utilities.token_helper import num_tokens_from_string

# TODO: Add loaders for PPT, and other document types
DOCUMENT_TYPES = {
    ".txt": TextLoader,
    ".pdf": PDFPlumberLoader,  # PDFLoader,
    ".csv": CSVLoader,
    ".html": BSHTMLLoader,
    ".cpp": CodeLoader,
    ".c": CodeLoader,
    ".cc": CodeLoader,
    ".h": CodeLoader,
    ".py": CodeLoader,
    "xls": UnstructuredExcelLoader,
    "xlsx": UnstructuredExcelLoader,
}

WORD_DOC_TYPES = {".doc": Docx2txtLoader, ".docx": Docx2txtLoader}

# Default LibreOffice installation location
LIBRE_OFFICE = r"C:\\Program Files\\LibreOffice\\program\\soffice.exe"


def convert_word_doc_to_pdf(input_doc, out_folder):
    """Convert a single word document to a PDF using LibreOffice

    Args:
        input_doc (str): The input document path.
        out_folder (str): Output folder.
    """
    p = Popen(
        [
            LIBRE_OFFICE,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            out_folder,
            input_doc,
        ]
    )
    logging.debug([LIBRE_OFFICE, "--convert-to", "pdf", input_doc])
    p.communicate()


def load_single_document(file_path: str) -> List[Document]:
    # Loads a single document from a file path
    file_extension = os.path.splitext(file_path)[1]

    if file_extension.lower() in WORD_DOC_TYPES.keys():
        convert_word_doc_to_pdf(file_path, os.path.dirname(file_path))
        file_path = os.path.splitext(file_path)[0] + ".pdf"
        file_extension = ".pdf"

    loader_class = DOCUMENT_TYPES.get(file_extension.lower())

    if loader_class:
        loader = loader_class(file_path)
    else:
        logging.error(f"Unsupported file type: '{file_extension}', {file_path}")

    # Should return a list[Document] from within the current file.  For PDFs this looks like a document per page.
    try:
        documents = loader.load()

        for doc in documents:
            # get the file name
            doc.metadata["filename"] = os.path.basename(file_path)

        return documents
    except Exception as e:
        err = f"Could not load {file_path}, {e}"
        logging.debug(err)
        raise ValueError(err)


def load_documents(source_dir: str) -> List[Document]:
    """Loads all documents from the source documents directory

    Args:
        source_dir (str): Source directory

    Returns:
        List[Document]: List of documents
    """
    all_files = os.listdir(source_dir)

    paths = []
    for file_path in all_files:
        file_extension = os.path.splitext(file_path)[1]
        source_file_path = os.path.join(source_dir, file_path)

        if file_extension in DOCUMENT_TYPES.keys():
            paths.append(source_file_path)

    docs = []
    for file_path in paths:
        try:
            documents = load_single_document(file_path)
            if documents:
                docs.extend(documents)
        except Exception as e:
            logging.debug(f"Error loading {file_path}: {e}")

    return docs


def load_and_split_documents(
    document_directory: str,
    split_documents: bool,
    chunk_size: int,
    chunk_overlap: int,
) -> List[Document]:
    # Check if the document_directory is a single file or a path
    if os.path.isfile(document_directory):
        documents = load_single_document(document_directory)
    else:
        documents = load_documents(document_directory)

    if split_documents:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=num_tokens_from_string
        )
        texts = text_splitter.split_documents(documents)

        logging.debug(
            f"Split into {len(texts)} chunks of text (chunk_size: {chunk_size}, chunk_overlap: {chunk_overlap})"
        )
    else:
        texts = documents

    # Remove TLP:WHITE from the page_content
    for text in texts:
        if "TLP:WHITE" in text.page_content:
            text.page_content = text.page_content.replace("TLP:WHITE", "")

    logging.debug(
        f"Loaded {len(documents)} pages of documents from {document_directory}"
    )

    return texts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test loading and splitting documents
    source = "/Repos/assistant/streamlit_ui.py"
    documents = load_and_split_documents(source, True, 1000, 100)
    print(len(documents))

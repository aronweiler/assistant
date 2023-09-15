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
from langchain.document_loaders import (
    CSVLoader,
    TextLoader,
    Docx2txtLoader,
    BSHTMLLoader,
    PDFPlumberLoader,
    UnstructuredExcelLoader,
)

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
}

WORD_DOC_TYPES = {".doc": Docx2txtLoader, ".docx": Docx2txtLoader}

EXCEL_DOC_TYPES = {".xls": UnstructuredExcelLoader, ".xlsx": UnstructuredExcelLoader}

# Default LibreOffice installation location
LIBRE_OFFICE_DEFAULT = "/Program Files/LibreOffice/program/soffice.exe"

def get_libre_office_path() -> str:
    """Gets the LibreOffice installation path

    Returns:
        str: The path to the LibreOffice installation
    """
    # Check if the LIBRE_OFFICE_PATH environment variable is set
    if "LIBRE_OFFICE_PATH" in os.environ:
        return os.environ["LIBRE_OFFICE_PATH"]
    else:
        # Check if the default path exists
        if os.path.exists(LIBRE_OFFICE_DEFAULT):
            return LIBRE_OFFICE_DEFAULT
        else:
            raise ValueError(
                f"Could not find LibreOffice installation.  Please set the LIBRE_OFFICE_PATH environment variable to the installation path."
            )

def convert_word_doc_to_pdf(input_doc, out_folder):
    """Convert a single word document to a PDF using LibreOffice

    Args:
        input_doc (str): The input document path.
        out_folder (str): Output folder.
    """
    # Get the path from the input_doc
    # Don't need this here yet
    # cwd = os.path.dirname(input_doc)

    p = Popen(
        [
            get_libre_office_path(),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            out_folder,
            input_doc,
        ],
    )
    logging.debug([get_libre_office_path(), "--convert-to", "pdf", input_doc])
    p.communicate()


def convert_excel_to_csv(input_doc, out_folder):
    """Convert a single excel document to a multiple CSVs (per sheet) using LibreOffice

    Args:
        input_doc (str): The input document path.
        out_folder (str): Output folder.
    """
    # Get the path from the input_doc
    cwd = os.path.dirname(input_doc)
    # Get the file name without the path
    input_doc = os.path.basename(input_doc)

    p = Popen(
        [
            get_libre_office_path(),
            "--headless",
            "--convert-to",
            'csv:Text - txt - csv (StarCalc):44,34,UTF8,1,,0,false,true,false,false,false,-1',
            input_doc,
        ],
        cwd=cwd,
    )
    logging.debug([get_libre_office_path(), "--convert-to", "csv", input_doc])
    p.communicate()


def load_single_document(file_path: str) -> List[Document]:
    # Loads a single document from a file path
    file_extension = os.path.splitext(file_path)[1]

    loader_class = DOCUMENT_TYPES.get(file_extension.lower())

    if loader_class:
        loader = loader_class(file_path)

        # Should return a list[Document] from within the current file.  For PDFs this looks like a document per page.
        try:
            documents = loader.load()

            for doc in documents:
                # get the file name
                doc.metadata["filename"] = os.path.basename(file_path)
                if "page" not in doc.metadata:
                    doc.metadata["page"] = "N/A"

            return documents
        except Exception as e:
            err = f"Could not load {file_path}, {e}"
            logging.debug(err)
            raise ValueError(err)
    else:
        logging.error(f"Unsupported file type: '{file_extension}', {file_path}")


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

def convert_documents(source_dir: str):
    """Converts all Excel and Word documents from the source directory to PDFs and CSVs

    Args:
        source_dir (str): Source directory
    """   
    all_files = os.listdir(source_dir)

    for file_path in all_files:
        file_extension = os.path.splitext(file_path)[1]
        source_file_path = os.path.join(source_dir, file_path)

        if file_extension in WORD_DOC_TYPES.keys():
            convert_word_doc_to_pdf(source_file_path, source_dir)
        elif file_extension in EXCEL_DOC_TYPES.keys():
            convert_excel_to_csv(source_file_path, source_dir)


def load_and_split_documents(
    document_directory: str,
    split_documents: bool,
    chunk_size: int,
    chunk_overlap: int,
) -> List[Document]:
    
    # only accept directories
    if not os.path.isdir(document_directory):
        raise ValueError(f"document_directory must be a directory: {document_directory}")

    # Pre-convert the word docs to PDFs and the excel docs to csvs
    convert_documents(document_directory)

    documents = load_documents(document_directory)

    if documents:
        if split_documents:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=num_tokens_from_string,
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
    source = "/Repos/sample_docs/parks"
    documents = load_and_split_documents(source, True, 1000, 100)
    print(len(documents))

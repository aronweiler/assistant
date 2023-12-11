import logging
import os
import sys
from subprocess import Popen
from typing import List
import asyncio

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
    ".pdf": PDFPlumberLoader,
    ".csv": CSVLoader,
    ".ods": UnstructuredExcelLoader,
    ".xls": UnstructuredExcelLoader,
    ".xlsx": UnstructuredExcelLoader,
    ".html": BSHTMLLoader,
    ".htm": BSHTMLLoader,
    ".cpp": CodeLoader,
    ".c": CodeLoader,
    ".cc": CodeLoader,
    ".h": CodeLoader,
    ".py": CodeLoader,
}

DOCUMENT_CLASSIFICATIONS = {
    ".txt": "Document",
    ".pdf": "Document",
    ".csv": "Spreadsheet",
    ".xls": "Spreadsheet",
    ".xlsx": "Spreadsheet",
    ".ods": "Spreadsheet",
    # ".html": "Webpage",
    ".cpp": "Code",
    ".c": "Code",
    ".cc": "Code",
    ".h": "Code",
    ".py": "Code",
}

WORD_DOC_TYPES = {".doc": Docx2txtLoader, ".docx": Docx2txtLoader}

EXCEL_DOC_TYPES = {
    ".xls": UnstructuredExcelLoader,
    ".xlsx": UnstructuredExcelLoader,
    ".ods": UnstructuredExcelLoader,
}

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
            os.path.abspath(input_doc),
        ],
    )
    logging.debug([get_libre_office_path(), "--convert-to", "pdf", input_doc])
    p.communicate()


# Not used at the moment, but if we need to pull data from excel docs into csv, we can use this
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
            "csv:Text - txt - csv (StarCalc):44,34,UTF8,1,,0,false,true,false,false,false,-1",
            "--outdir",
            out_folder,
            input_doc,
        ],
        cwd=cwd,
    )
    logging.debug([get_libre_office_path(), "--convert-to", "csv", input_doc])
    p.communicate()


async def load_single_document(
    file_path: str, converted_file_maps: dict
) -> List[Document]:
    # Loads a single document from a file path
    file_extension = os.path.splitext(file_path)[1]

    loader_class = DOCUMENT_TYPES.get(file_extension.lower())

    if loader_class:
        if type(loader_class) == UnstructuredExcelLoader:
            # Special... thanks a lot crap design
            loader = loader_class(file_path, mode="elements")
        else:
            loader = loader_class(file_path)

        # Should return a list[Document] from within the current file.  For PDFs this looks like a document per page.
        try:
            documents = loader.load()

            for doc in documents:
                # get the file name
                if file_path in converted_file_maps:
                    # If it's in the converted files, get the original filename
                    doc.metadata["filename"] = os.path.basename(
                        converted_file_maps[file_path]
                    )
                else:
                    doc.metadata["filename"] = os.path.basename(file_path)

                if "page" not in doc.metadata:
                    doc.metadata["page"] = "N/A"

                if "classification" not in doc.metadata:
                    doc.metadata["classification"] = DOCUMENT_CLASSIFICATIONS.get(
                        file_extension.lower(), "Document"
                    )

            return documents
        except Exception as e:
            err = f"Could not load {file_path}, {e}"
            logging.debug(err)
            raise ValueError(err)
    else:
        logging.error(f"Unsupported file type: '{file_extension}', {file_path}")


async def load_documents(source_dir: str, converted_file_maps: dict) -> List[Document]:
    all_files = os.listdir(source_dir)

    paths = []
    for file_path in all_files:
        file_extension = os.path.splitext(file_path)[1]
        source_file_path = os.path.join(source_dir, file_path)

        if file_extension in DOCUMENT_TYPES.keys():
            paths.append(source_file_path)

    tasks = [
        load_single_document(file_path, converted_file_maps) for file_path in paths
    ]
    docs = []
    for task in asyncio.as_completed(tasks):
        try:
            documents = await task
            if documents:
                docs.extend(documents)
        except Exception as e:
            logging.error(f"Error loading document: {e}")

    return docs


def convert_documents(source_dir: str):
    """Converts all Excel and Word documents from the source directory to PDFs and CSVs

    Args:
        source_dir (str): Source directory
    """
    all_files = os.listdir(source_dir)

    converted_file_maps = {}
    for file_path in all_files:
        file_extension = os.path.splitext(file_path)[1]
        source_file_path = os.path.join(source_dir, file_path)

        if file_extension in WORD_DOC_TYPES.keys():
            convert_word_doc_to_pdf(source_file_path, source_dir)
            # Kind of a reverse map
            converted_file_maps[
                os.path.splitext(source_file_path)[0] + ".pdf"
            ] = source_file_path
        # elif file_extension in EXCEL_DOC_TYPES.keys():
        #     convert_excel_to_csv(source_file_path, source_dir)

    return converted_file_maps


async def load_and_split_documents(
    document_directory: str,
    split_documents: bool,
    is_code: bool,
    chunk_size: int,
    chunk_overlap: int,
) -> List[Document]:
    if not os.path.isdir(document_directory):
        raise ValueError(
            f"document_directory must be a directory: {document_directory}"
        )

    # Pre-convert the word docs to PDFs and the excel docs to csvs
    converted_file_maps = convert_documents(document_directory)

    documents:List[Document] = await load_documents(document_directory, converted_file_maps)

    if documents and split_documents and not is_code:
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

    for text in texts:
        if "TLP:WHITE" in text.page_content:
            text.page_content = text.page_content.replace("TLP:WHITE", "")

    logging.debug(
        f"Loaded {len(documents)} pages of documents from {document_directory}"
    )

    return texts


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOGGING_LEVEL", "INFO"))

    # Test loading and splitting documents
    source = "/Repos/sample_docs/cpp/Dave/StateMachine"
    documents = asyncio.run(
        load_and_split_documents(
            document_directory=source,
            split_documents=False,
            is_code=False,
            chunk_size=1000,
            chunk_overlap=0,
        )
    )
    print(len(documents))

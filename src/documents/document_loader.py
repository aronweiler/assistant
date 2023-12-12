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

# Default LibreOffice installation location
LIBRE_OFFICE_DEFAULT = "/Program Files/LibreOffice/program/soffice.exe"


class DocumentLoader:
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

    def __init__(self):
        self.converted_file_maps = {}

    @staticmethod
    def get_libre_office_path() -> str:
        if "LIBRE_OFFICE_PATH" in os.environ:
            return os.environ["LIBRE_OFFICE_PATH"]
        elif os.path.exists(LIBRE_OFFICE_DEFAULT):
            return LIBRE_OFFICE_DEFAULT
        else:
            raise ValueError(
                f"Could not find LibreOffice installation. Please set the LIBRE_OFFICE_PATH environment variable to the installation path."
            )

    def convert_word_doc_to_pdf(self, input_doc, out_folder):
        p = Popen(
            [
                self.get_libre_office_path(),
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                out_folder,
                os.path.abspath(input_doc),
            ],
        )
        logging.debug([self.get_libre_office_path(), "--convert-to", "pdf", input_doc])
        p.communicate()

    async def load_single_document(self, file_path: str) -> List[Document]:
        file_extension = os.path.splitext(file_path)[1]

        loader_class = self.DOCUMENT_TYPES.get(file_extension.lower())

        if loader_class:
            loader = loader_class(file_path)
            try:
                documents = loader.load()
                for doc in documents:
                    doc.metadata["filename"] = os.path.basename(
                        self.converted_file_maps.get(file_path, file_path)
                    )
                    doc.metadata.setdefault("page", "N/A")
                    doc.metadata.setdefault(
                        "classification",
                        self.DOCUMENT_CLASSIFICATIONS.get(
                            file_extension.lower(), "Document"
                        ),
                    )
                return documents
            except Exception as e:
                err = f"Could not load {file_path}, {e}"
                logging.debug(err)
                raise ValueError(err)
        else:
            logging.error(f"Unsupported file type: '{file_extension}', {file_path}")

    async def load_documents(self, source_dir: str) -> List[Document]:
        all_files = os.listdir(source_dir)
        paths = [
            os.path.join(source_dir, file_path)
            for file_path in all_files
            if os.path.splitext(file_path)[1] in self.DOCUMENT_TYPES
        ]

        tasks = [self.load_single_document(file_path) for file_path in paths]
        documents = await asyncio.gather(*tasks, return_exceptions=True)
        documents = [
            doc
            for doc_list in documents
            if isinstance(doc_list, list)
            for doc in doc_list
        ]
        return documents

    def convert_documents(self, source_dir: str):
        all_files = os.listdir(source_dir)
        for file_path in all_files:
            file_extension = os.path.splitext(file_path)[1]
            source_file_path = os.path.join(source_dir, file_path)

            if file_extension in self.WORD_DOC_TYPES:
                self.convert_word_doc_to_pdf(source_file_path, source_dir)
                self.converted_file_maps[
                    os.path.splitext(source_file_path)[0] + ".pdf"
                ] = source_file_path

        return self.converted_file_maps

    async def load_and_split_documents(
        self,
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

        self.converted_file_maps = self.convert_documents(document_directory)

        documents = await self.load_documents(document_directory)

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
            text.page_content = text.page_content.replace("TLP:WHITE", "")

        logging.debug(
            f"Loaded {len(documents)} pages of documents from {document_directory}"
        )

        return texts


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOGGING_LEVEL", "INFO"))

    # Test loading and splitting documents
    source = "/Repos/sample_docs/cpp/Dave/StateMachine"
    document_loader = DocumentLoader()
    documents = asyncio.run(
        document_loader.load_and_split_documents(
            document_directory=source,
            split_documents=False,
            is_code=False,
            chunk_size=1000,
            chunk_overlap=0,
        )
    )
    print(len(documents))

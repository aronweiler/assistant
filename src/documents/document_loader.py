import logging
import multiprocessing
import os

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from subprocess import Popen
from typing import List

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Custom loaders
from documents.pdf_loader import PDFLoader
from documents.code_loader import CodeLoader

# TODO: Add loaders for PPT, and other document types
from langchain.document_loaders import CSVLoader, TextLoader, Docx2txtLoader, BSHTMLLoader


# TODO: Add loaders for PPT, and other document types
DOCUMENT_TYPES = {
    ".txt": TextLoader,
    ".pdf": PDFLoader,
    ".csv": CSVLoader,
    ".html": BSHTMLLoader,
    ".cpp" : CodeLoader,
    ".c" : CodeLoader,
    ".cc" : CodeLoader,
    ".h" : CodeLoader,
}

WORD_DOC_TYPES = {".doc": Docx2txtLoader, ".docx": Docx2txtLoader}

# default LibreOffice installation location
LIBRE_OFFICE = r"C:\\Program Files\\LibreOffice\\program\\soffice.exe"


def convert_word_docs_to_pdf(source_dir: str):
    all_files = os.listdir(source_dir)

    for file_path in all_files:
        file_extension = os.path.splitext(file_path)[1]
        source_file_path = os.path.join(source_dir, file_path)

        if file_extension in WORD_DOC_TYPES.keys():
            convert_word_doc_to_pdf(source_file_path, source_dir)


def convert_word_doc_to_pdf(input_doc, out_folder):
    """Convert a single word document to a PDF using LibreOffice

    NOTE: This cannot be done multi-threaded, as there are issues with using a single LibreOffice instance across multiple threads

    Args:
        input_doc (_type_): the input document
        out_folder (_type_): output folder
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
    loader_class = DOCUMENT_TYPES.get(file_extension)

    if loader_class:
        loader = loader_class(file_path)
    else:
        raise ValueError(f"Document type is undefined, {file_path}")

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
        raise (ValueError(err))


def load_document_batch(filepaths):
    logging.debug("Loading document batch")
    # create a thread pool
    with ThreadPoolExecutor(len(filepaths)) as exe:
        # load files
        futures = [exe.submit(load_single_document, name) for name in filepaths]
        # collect data
        data_list = [future.result() for future in futures]
        # return data and file paths
        return (data_list, filepaths)


def load_documents(source_dir: str) -> List[Document]:
    """Loads all documents from the source documents directory

    Args:
        source_dir (str): Source directory

    Returns:
        List[Document]: List of documents
    """

    # First we have to convert all of the doc/docx files to PDF in order to reap the benbens of the sick pagination and HTML conversion stuff
    convert_word_docs_to_pdf(source_dir)

    # pull the list of files again after the word doc conversions
    all_files = os.listdir(source_dir)

    paths = []
    for file_path in all_files:
        file_extension = os.path.splitext(file_path)[1]
        source_file_path = os.path.join(source_dir, file_path)

        if file_extension in DOCUMENT_TYPES.keys():
            paths.append(source_file_path)

    num_processors = multiprocessing.cpu_count()
    n_workers = min(num_processors, len(paths))
    chunksize = round(len(paths) / n_workers)
    docs = []
    with ProcessPoolExecutor(n_workers) as executor:
        futures = []
        # split the load operations into chunks
        for i in range(0, len(paths), chunksize):
            # select a chunk of filenames
            filepaths = paths[i : (i + chunksize)]
            # submit the task
            future = executor.submit(load_document_batch, filepaths)
            futures.append(future)
        # process all results
        for future in as_completed(futures):
            # open the file and load the data
            contents, _ = future.result()

            if type(contents) == list:
                if contents[0] != None:
                    for doc in contents[0]:
                        docs.append(doc)
            else:
                docs.extend(contents)

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
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        texts = text_splitter.split_documents(documents)

        logging.debug(
            f"Split into {len(texts)} chunks of text (chunk_size: {chunk_size}, chunk_overlap: {chunk_overlap})"
        )
    else:
        texts = documents

    # Remove TLP:WHITE from the page_content
    # For some insane reason, this is something that some of the PDFs have in them, and it's not useful for us
    for text in texts:
        # if the page_content contains 'TLP:WHITE\t\n' then remove it
        if "TLP:WHITE" in text.page_content:
            text.page_content = text.page_content.replace("TLP:WHITE", "")

    logging.debug(
        f"Loaded {len(documents)} pages of documents from {document_directory}"
    )

    return texts
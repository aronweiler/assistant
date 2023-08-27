import logging
from langchain.document_loaders import PDFMinerPDFasHTMLLoader
from langchain.docstore.document import Document
from bs4 import BeautifulSoup
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from langchain.document_loaders import BSHTMLLoader


class HTMLLoader:
    def __init__(self, file_path=None):
        self.file_path = file_path

    def load(self):
        if self.file_path is None:
            logging.debug("File path is None")
            return None

        loader = BSHTMLLoader(self.file_path, open_encoding="utf-8")

        data = loader.load()

        return data


# html_loader = HTMLLoader(
#     "C:\\Repos\\DocTalk\\src\\runners\\cvss\\documents\\spec\\CVSS v3.1 Specification Document.html"
# )
# docs = html_loader.load()

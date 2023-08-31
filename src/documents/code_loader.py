from langchain.schema import Document
from documents.codesplitter.main import run

class CodeLoader:
    def __init__(self, file_path=None):
        self.file_path = file_path

    def load(self):
        nodes = run(path=self.file_path)
        
        data = []
        # Create a list of Document objects from the nodes, using the text as the content, and the rest of the data as metadata
        # Fields: 'type', 'signature', 'text', 'file_loc', 'includes', 'access_specifier', 'class'
        for node in nodes:
            data.append(Document(
                page_content=node['text'],
                metadata=node
            ))

        return data


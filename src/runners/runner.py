import logging
from abc import ABC, abstractmethod
from ai.abstract_ai import AbstractAI


class Runner(ABC):
    @abstractmethod
    def run(self, abstract_ai: AbstractAI):
        pass

    @abstractmethod
    def configure(self):
        pass

    def get_source_docs_to_print(self, source_documents=None):
        if source_documents is None:
            return ""
        else:
            return "\n".join(
                [
                    f"\t-{doc['document']} - Page {doc['page']}"
                    if isinstance(doc, dict) and "page" in doc
                    else f"\t-{doc}"
                    for doc in source_documents
                ]
            )

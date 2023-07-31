import logging
import time
from ai.abstract_ai import AbstractAI
from runners.runner import Runner

from utilities.pretty_print import pretty_print_conversation


class ConsoleRunner(Runner):
    def __init__(self):
        pass

    def configure(self):
        pass

    def run(self, abstract_ai: AbstractAI):
        while True:
            # Get the query, which can be multiple lines
            print("Query (Enter twice to run, X to exit):")

            query = self.get_multi_line_console_input()

            # Run the query
            result = abstract_ai.query(query)

            # print the result
            pretty_print_conversation(result.result_string)

            source_docs = self.get_source_docs_to_print(
                result.source_documents, "green"
            )

            if source_docs != "":
                pretty_print_conversation("Source documents:\n" + source_docs, "blue")

    def get_multi_line_console_input(self):
        # Get the query, which can be multiple lines, until the user presses enter twice
        query = ""
        while True:
            line = input()
            if line == "":
                break
            query += line + "\n"

        return query

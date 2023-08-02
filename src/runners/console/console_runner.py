import logging
import time
from ai.abstract_ai import AbstractLLM
from runners.runner import Runner
from db.database.models import User

from utilities.pretty_print import pretty_print_conversation


class ConsoleRunner(Runner):
    def __init__(self, user_information):
        self.user_information = user_information["user_information"]
        self.user = User(name=self.user_information["user_name"], email=self.user_information["email_address"], location=self.user_information["location"])

    def configure(self):
        pass

    def run(self, abstract_ai: AbstractLLM):
        while True:   

            query = input("Query (X to exit):")

            # Run the query
            result = abstract_ai.query(query, self.user)

            # print the result
            pretty_print_conversation(result)

            # if result.source_documents:
            #     source_docs = self.get_source_docs_to_print(
            #         result.source_documents
            #     )

            #     if len(source_docs) > 0:
            #         pretty_print_conversation("Source documents:\n" + source_docs, "blue")

            

    def get_multi_line_console_input(self):
        # Get the query, which can be multiple lines, until the user presses enter twice
        query = ""
        while True:
            line = input()
            if line == "":
                break
            query += line + "\n"

        return query

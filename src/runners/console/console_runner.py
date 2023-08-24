import logging
import time
from ai.abstract_ai import AbstractAI
from runners.runner import Runner
from db.database.models import User
from db.models.users import Users


from utilities.pretty_print import pretty_print_conversation


class ConsoleRunner(Runner):
    def __init__(self, arguments):
        email = arguments["user_information"]["email_address"]

        self.users = Users(arguments["db_env_location"])
        with self.users.session_context(self.users.Session()) as session:
            self.user = self.users.find_user_by_email(
                session,
                email=email,
                eager_load=[],
            )

            self.user_id = self.user.id

    def configure(self):
        pass

    def run(self, abstract_ai: AbstractAI):
        # TODO: Remove this- testing the voice prompt only
        # from runners.voice.prompts import FINAL_REPHRASE_PROMPT
        # abstract_ai.final_rephrase_prompt = FINAL_REPHRASE_PROMPT

        while True:
            query = input("Query (X to exit):")

            # Run the query
            result = abstract_ai.query(query, self.user_id)

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

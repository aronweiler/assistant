import logging
from datetime import datetime

from db.database.models import User
from db.models.users import Users
from configuration.ai_configuration import AIConfiguration
from ai.abstract_ai import AbstractAI
from llms.abstract_llm import AbstractLLM
from llms.llm_result import LLMResult


class GeneralAI(AbstractAI):
    def __init__(self, ai_configuration: AIConfiguration):
        self.ai_configuration = ai_configuration

        # Initialize the AbstractLLM and dependent AIs
        self.configure()

        self.users = Users(self.ai_configuration.db_env_location)

    def query(self, query, user_id):
        """Query the AI

        Args:
            query (str): Query for the AI
            user_id (int): ID of the user making the query

        Returns:
            str: Result of the query
        """

        self.llm: AbstractLLM

        # Get the user information
        with self.users.session_context(self.users.Session()) as session:
            current_user = self.users.get_user(
                session, user_id, eager_load=[User.user_settings]
            )

            self.user_name = current_user.name
            self.user_email = current_user.email
            self.user_id = current_user.id

        try:
            system_information = f"Current Date/Time: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}. Current Time Zone: {datetime.now().astimezone().tzinfo}"

            # Send it down the line
            response: LLMResult = self.llm.query(
                query,
                user_id=self.user_id,
                user_name=self.user_name,
                user_email=self.user_email,
                system_information=system_information,
            )

            logging.debug(f"Response from LLM: {response.result_string}")

            # General AI returns a string
            return response.result_string
        except Exception as e:
            logging.exception(e)
            return "Sorry, I'm not feeling well right now. Please try again later."

# See: https://python.langchain.com/docs/integrations/toolkits/gmail
import os
import logging

from langchain.tools.gmail.utils import build_resource_service, get_gmail_credentials
from langchain.agents.agent_toolkits import GmailToolkit


class GmailTool:
    def __init__(self):
        # Get the credentials file location from the environment variable
        credentials_file = os.environ.get("GOOGLE_CREDENTIALS_FILE_LOCATION", None)

        if credentials_file is None:
            logging.warning(
                "GOOGLE_CREDENTIALS_FILE_LOCATION environment variable is not set, GmailTool will not be available"
            )
            self.toolkit = None
            return

        try:
            # Can review scopes here https://developers.google.com/gmail/api/auth/scopes
            # For instance, readonly scope is 'https://www.googleapis.com/auth/gmail.readonly'
            credentials = get_gmail_credentials(
                token_file="token.json",
                scopes=["https://mail.google.com/"],
                client_secrets_file=credentials_file,
            )
            api_resource = build_resource_service(credentials=credentials)
            self.toolkit = GmailToolkit(api_resource=api_resource)
        except Exception as e:
            logging.error(f"Error initializing GmailTool: {e}")
            self.toolkit = None

    def search_for_emails(self, query: str):
        search_gmail = next(
            (tool for tool in self.toolkit.get_tools() if tool.name == "search_gmail"),
            None,
        )

        results = search_gmail.run(tool_input=query)

        emails = [
            {
                "id": result["id"],
                "thread_id": result["threadId"],
                "subject": result["subject"],
                "snippet": result["snippet"],
                "sender": result["sender"],
            }
            for result in results
        ]

        if len(emails) == 0:
            return "No emails found, please adjust your search parameters."

        return emails

    def get_email_by_id(self, message_id: str):
        get_gmail_thread = next(
            (
                tool
                for tool in self.toolkit.get_tools()
                if tool.name == "get_gmail_message"
            ),
            None,
        )

        try:
            results = get_gmail_thread.run(tool_input=message_id)
        except Exception as e:
            logging.error(f"Error getting email by id: {e}")
            return e

        return results

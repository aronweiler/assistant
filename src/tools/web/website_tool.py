import requests
from typing import List
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter


# Add the project root to the python path at runtime
import sys
from pathlib import Path
from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.llm_helper import get_tool_llm

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utilities.token_helper import num_tokens_from_string


class WebsiteTool:
    def __init__(
        self,
        configuration,
        conversation_manager: ConversationManager,
    ):
        """
        Initializes the WebsiteTool with a given configuration and an conversation manager.

        :param configuration: Configuration settings for the tool.
        :param conversation_manager: The manager that handles interactions with language models.
        """
        self.configuration = configuration
        self.conversation_manager = conversation_manager

    def get_text_from_website(self, url: str, user_query: str) -> str:
        """Reads content from a website"""
        full_html = requests.get(url).text

        # parse using beautiful soup
        soup = BeautifulSoup(full_html, "html.parser")
        raw_text_no_html = soup.get_text(strip=True, separator=" ")

        self.get_summary_or_text(raw_text_no_html, user_query)

        return raw_text_no_html

    def get_summary_or_text(self, text: str, user_query: str) -> str:
        """Returns a summary of the text if it is larger than the max chunk size, otherwise returns the text"""
        additional_settings = self.configuration["tool_configurations"][
            self.get_text_from_website.__name__
        ].get("additional_settings", 2048)

        max_chunk_size = additional_settings["max_chunk_size"]

        num_tokens = num_tokens_from_string(text)
        if num_tokens > max_chunk_size:
            return self.get_summary(
                text=text, user_query=user_query, max_chunk_size=max_chunk_size
            )
        else:
            return text

    def get_summary(self, text: str, user_query: str, max_chunk_size: int) -> str:
        """Returns a summary of the text"""

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=50,
            length_function=num_tokens_from_string,
        )

        split_text = splitter.split_text(text)

        # Initialize language model for prediction.
        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.get_text_from_website.__name__,
            streaming=True,
        )

        existing_summary = None

        for chunk in split_text:
            if not existing_summary:
                prompt = self.conversation_manager.prompt_manager.get_prompt(
                    category="summary",
                    prompt_name="DETAILED_DOCUMENT_CHUNK_SUMMARY_TEMPLATE",
                ).format(existing_answer=existing_summary, text=chunk, query=user_query)
            else:
                prompt = self.conversation_manager.prompt_manager.get_prompt(
                    category="summary", prompt_name="SIMPLE_REFINE_TEMPLATE"
                ).format(existing_answer=existing_summary, text=chunk, query=user_query)

            existing_summary = llm.predict(
                prompt=prompt, callbacks=self.conversation_manager.agent_callbacks
            )

        return existing_summary

import requests
from typing import List
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter


# Add the project root to the python path at runtime
import sys
from pathlib import Path
from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.utilities.llm_helper import get_tool_llm
from src.ai.prompts.prompt_models.document_summary import DocumentChunkSummaryInput, DocumentSummaryOutput, DocumentQuerySummaryRefineInput
from src.ai.prompts.query_helper import QueryHelper
from src.ai.tools.tool_registry import register_tool, tool_class

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utilities.token_helper import num_tokens_from_string


@tool_class
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

    @register_tool(
        display_name="Get Text From Website",
        help_text="Reads text from the specified URL.",
        requires_documents=False,
        description="Reads text from the specified URL.",
        additional_instructions="Pass in the URL of the target website, along with the user's original query.",
        category="Web",
    )
    def get_text_from_website(self, url: str, user_query: str) -> str:
        """Reads content from a website"""
        full_html = requests.get(url).text

        # parse using beautiful soup
        soup = BeautifulSoup(full_html, "html.parser")
        raw_text_no_html = soup.get_text(strip=True, separator=" ")

        return self.get_summary_or_text(raw_text_no_html, url, user_query)

    def get_summary_or_text(self, text: str, url: str, user_query: str) -> str:
        """Returns a summary of the text if it is larger than the max chunk size, otherwise returns the text"""
        additional_settings = self.configuration["tool_configurations"][
            self.get_text_from_website.__name__
        ]["additional_settings"]

        max_chunk_size = additional_settings["max_chunk_size"]["value"]

        num_tokens = num_tokens_from_string(text)
        if num_tokens > max_chunk_size:
            summary = self.get_summary(
                text=text, user_query=user_query, max_chunk_size=max_chunk_size
            )
            return f"The chunk size of {max_chunk_size} was exceeded, so here is a summary of the user's request for {url}:\n\n{summary}"
        else:
            return f"Here is the raw text of {url}:\n\n{text}"

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
            # callbacks=self.conversation_manager.agent_callbacks,
        )

        existing_summary = None
        query_helper = QueryHelper(self.conversation_manager.prompt_manager)

        for chunk in split_text:
            if not existing_summary:
                input_object = DocumentChunkSummaryInput(chunk_text=chunk)

                result = query_helper.query_llm(
                    llm=llm,
                    prompt_template_name="DETAILED_DOCUMENT_CHUNK_SUMMARY_TEMPLATE",
                    input_class_instance=input_object,
                    output_class_type=DocumentSummaryOutput,
                )

                existing_summary = result.summary
            else:
                input_object = DocumentQuerySummaryRefineInput(text=chunk, existing_answer=existing_summary, query=user_query)

                result = query_helper.query_llm(
                    llm=llm,
                    prompt_template_name="SIMPLE_REFINE_TEMPLATE",
                    input_class_instance=input_object,
                    output_class_type=DocumentSummaryOutput,
                )

                existing_summary = result.summary                

        return existing_summary

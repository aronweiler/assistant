import requests
from typing import List
from bs4 import BeautifulSoup
from langchain.document_loaders import BSHTMLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


# Add the project root to the python path at runtime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from utilities.token_helper import simple_get_tokens_for_message
from tools.results.summarize_result import SummarizeResult

# A simple wrapper around the requests library


        # Args:
        #     url (str): URL to send the request to
        #     search_term (str): The term to search for
        #     top_k (int): The number of results to return
        #     params (dict[str, str]): optional list of tuples or bytes to send in the query string to the url

        # Returns:
        #     List[str]: Relevant chunks of text from the website"""

class RequestsTool:
    def search_website(
        self, url: str, search_term: str, top_k: int = 3, params: dict[str, str] = None
    ) -> List[str]:
        """Website search tool. Use this when you need to get content from a specific website."""
        full_html = requests.get(url, params=params).text

        # parse using beautiful soup
        soup = BeautifulSoup(full_html, "html.parser")
        # Split the text up using
        raw_text = soup.get_text(strip=True, separator="\n")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=256,
            chunk_overlap=25,
            length_function=simple_get_tokens_for_message,
        )

        split_text = splitter.split_text(raw_text)

        # Create a summarizer result and then do a similarity search
        scrape_result = SummarizeResult(split_text)
        search_results = scrape_result.search_results(search_term, n=top_k)

        return "\n\n".join([r[0] for r in search_results])

    def get_request(self, url: str, params: dict[str, str] = None) -> str:
        """A RAW portal to the internet. Use this when you need to get the raw content from a URL. Input should be a  url (i.e. https://www.google.com). The output will be the text response of the GET request.

        Args:
            url (str): URL to send the request to
            params (dict[str, str]): optional list of tuples or bytes to send in the query string

        Returns:
            str: The raw HTML of the response"""
        return requests.get(url, params=params).text

    def post_request(self, url: str, data: dict[str, str] = None) -> str:
        """Use this when you want to POST to a website.
            Input should be a json string with two keys: "url" and "data".
            The value of "url" should be a string, and the value of "data" should be a dictionary of
            key-value pairs you want to POST to the url.
            Be careful to always use double quotes for strings in the json string
            The output will be the text response of the POST request.

        Args:
            url (str): URL to send the request to
            data (dict[str, str]): optional list of tuples, bytes, or file-like object to send in the body of the request

            Returns:
                str: The text of the response"""

        return requests.post(url, data=data)


# Testing
if __name__ == "__main__":
    # Test get_website
    print("Testing get_website")

    result = RequestsTool().search_website("https://www.cnn.com", "Trump")

    print(result)

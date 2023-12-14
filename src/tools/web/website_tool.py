import requests
from typing import List
from bs4 import BeautifulSoup


# Add the project root to the python path at runtime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utilities.token_helper import num_tokens_from_string

class WebsiteTool:
    def get_text_from_website(self, url: str, url_params: dict[str, str] = None) -> List[str]:
        """Reads content from a website"""
        full_html = requests.get(url, params=url_params).text

        # parse using beautiful soup
        soup = BeautifulSoup(full_html, "html.parser")
        raw_text_no_html = soup.get_text(strip=True, separator=" ")

        return raw_text_no_html

        # Check the configuration for the number of tokens to split on

        # If the total text is smaller than the size of the chunk, then just return the text

        # If the text is larger than the max chunk size, then split it up into chunks

        # Summarize each chunk and then return the results

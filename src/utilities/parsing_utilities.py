import re
import json
import os
import logging

from src.utilities.json_repair import JsonRepair

# Configure logging
logging.basicConfig(level=logging.getLevelName(os.getenv('LOGGING_LEVEL', 'INFO')))
logger = logging.getLogger(__name__)


# Constants
JSON_CODE_BLOCK_START = '```json'
JSON_CODE_BLOCK_END = '```'


def extract_json_block(text):
    """
    Extract JSON from code blocks.

    :param text: String containing the text with potential JSON code blocks.
    :return: The extracted JSON string if found, otherwise None.
    """
    pattern = re.compile(r'```(?:json)?\n(.*?)```', re.DOTALL)
    try:
        match = pattern.search(text)
        return match.group(1).strip() if match else None
    except re.error as e:
        logger.error(f'Regex error occurred: {e}')
        return None


def parse_json(text: str) -> dict:
    """
    Parse a JSON string, repairing it if necessary.

    :param text: String containing the JSON to parse.
    :return: A dictionary representation of the JSON.
    """
    text = text.strip()

    # Check if the entire text is a JSON code block
    if text.startswith(JSON_CODE_BLOCK_START) and text.endswith(JSON_CODE_BLOCK_END):
        text = text[len(JSON_CODE_BLOCK_START):-len(JSON_CODE_BLOCK_END)].strip()

    # Extract JSON from within the text
    json_block = extract_json_block(text)
    if json_block is not None:
        text = json_block

    # Attempt to parse the JSON
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError as e:
        logger.warning('Failed to parse JSON, trying to repair it...')
        try:
            # Try to repair the JSON
            repaired_text = JsonRepair(text).repair()
            return json.loads(repaired_text, strict=False)
        except json.JSONDecodeError as e:
            error_msg = f'Failed to repair JSON. Original text: {text}, Error: {e}'
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    # Fallback if the text is not JSON
    logger.warning('Gave up on handling JSON, returning text as final_answer...')
    return {'final_answer': text}

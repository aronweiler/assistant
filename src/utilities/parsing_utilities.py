import re
import json
import os
import logging

from langchain.schema.language_model import BaseLanguageModel
from src.utilities.json_repair import JsonRepair

logging.basicConfig(level=os.getenv('LOGGING_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

def parse_json(text: str, llm: BaseLanguageModel) -> dict:
    original_text = text
    text = text.strip().replace('```json', '```json')

    # Define a pattern that matches the outermost JSON code block
    outermost_pattern = re.compile(r'(\`{3}json[\s\S]+?\`{3})(?=(\n\`{3})|$)', re.MULTILINE)

    # Search for the outermost JSON code block
    outermost_match = outermost_pattern.search(text)
    if outermost_match:
        # Extract the content of the outermost JSON code block
        json_block_content = outermost_match.group(1)[7:-3].strip()

        # Attempt to parse the JSON block
        try:
            json_block = json.loads(json_block_content, strict=False)
            return json_block
        except json.JSONDecodeError as e:
            logger.warning('Failed to parse JSON block, attempting repair.')
            # Attempt to repair the JSON block
            repaired_text = JsonRepair(json_block_content).repair()
            return parse_json(repaired_text, llm)

    # If no JSON structure is detected, return the text as the final answer
    logger.warning('Gave up on handling JSON, returning text as final_answer...')
    return {'final_answer': original_text}

# Note: The refactored code now uses a single pattern to match the outermost JSON code block and attempts to parse it. 
# The previous nested_pattern and other patterns have been removed as they were not correctly handling nested code blocks.
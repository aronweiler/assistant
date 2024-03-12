import re
import json
import os
import logging

from langchain.schema.language_model import BaseLanguageModel
from src.utilities.json_repair import JsonRepair

logging.basicConfig(level=os.getenv("LOGGING_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def parse_json(text: str, llm: BaseLanguageModel) -> dict:
    original_text = text
    text = text.strip().replace("```json", "```json")

    # Handle JSON code blocks (whole response)
    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3].strip()

    # Handle nested JSON code blocks
    nested_pattern = re.compile(r"(\`{3}json[\s\S]+?\`{3})", re.MULTILINE)
    matches = nested_pattern.findall(text)
    if matches:
        for match in matches:
            # Process each match
            processed_text = match[
                7:-3
            ].strip()  # Remove the markdown code block syntax
            try:
                # Attempt to parse the JSON
                json_block = json.loads(processed_text, strict=False)
                return json_block
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse JSON block, attempting repair.")
                # Attempt to repair the JSON block
                repaired_text = JsonRepair(processed_text).repair()
                return parse_json(repaired_text, llm)

    # Handle JSON code blocks (inside other text within a response)
    pattern = re.compile(r"```json\n(.*?)```", re.DOTALL)
    action_match = pattern.search(text)
    if action_match:
        logger.info("Handling JSON found inside of a code block...")
        text = action_match.group(1).strip()
        try:
            response = json.loads(text, strict=False)
            return response
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON, trying to repair it...")
            text = JsonRepair(text).repair()
            return parse_json(text, llm)

    # Handle JSON not in code blocks
    if (text.startswith("{") and text.endswith("}")) or (
        text.startswith("[") and text.endswith("]")
    ):
        logger.info("Handling JSON that is not inside of a code block...")
        try:
            return json.loads(text, strict=False)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON, trying to repair it...")
            text = JsonRepair(text).repair()
            return parse_json(text, llm)

    # If no JSON structure is detected, return the text as the final answer
    logger.warning("Gave up on handling JSON, returning text as final_answer...")
    return {"final_answer": text}


# Note: The example code for processing each matched JSON block is included in the nested_pattern handling section.
import re
import json
import os
import logging

from langchain.schema.language_model import BaseLanguageModel
from src.utilities.json_repair import JsonRepair

logging.basicConfig(level=os.getenv("LOGGING_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

def parse_json(text: str, llm: BaseLanguageModel) -> dict:
    
    # So....
    text = text.strip()
    
    # Hey look, another random thing to handle
    text = text.replace("``` json", "```json")

    # Handle JSON code blocks (whole response)
    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3]

        # Fucking...
        text = text.strip()

        # Sometimes there are two lines of ``` code block nonsense
        if text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

    # Annoying...
    text = text.strip()

    # Handle JSON code blocks (inside other text within a response)
    pattern = re.compile(r"```(?:json)?\n(.*?)```", re.DOTALL)

    try:
        action_match = pattern.search(text)
        if action_match is not None:
            logger.info("Handling JSON found inside of a code block...")
            # Handles the json inside of the code block
            text = action_match.group(1).strip()            
            response = json.loads(text, strict=False)
            return response
        elif (text.strip().startswith("{") and text.strip().endswith("}")) or (text.strip().startswith("[") and text.strip().endswith("]")):
            logger.info("Handling JSON that is not inside of a code block...")
            # Handles JSON responses that are not in code blocks
            return json.loads(text.strip(), strict=False)
        else:
            # Just return this as the answer??
            logger.warning("Gave up on handling JSON, returning text as final_answer...")
            return {"final_answer": text}
    except Exception as e:
        try:
            logger.warning("Failed to parse JSON, trying to repair it...")
            # Try to repair the JSON
            text = JsonRepair(text).repair()
            return parse_json(text, None)
        except Exception as e:         
            # Last-ditch effort, try to use the LLM to fix the JSON
            logger.warning("Failed to repair JSON, trying to use LLM to fix it...")
            if llm:
                llm_fixed_json = llm.predict(
                    f"The following is badly formatted JSON, please fix it (only fix the JSON, do not otherwise modify the content):\n{text}\n\nAI: Sure, here is the fixed JSON (without modifying the content):\n"
                )
                return parse_json(llm_fixed_json, None)
            else:
                logger.error("Failed to parse JSON, and no LLM was provided to try to fix it.")
                raise Exception(f"Could not parse LLM output: {text}") from e            

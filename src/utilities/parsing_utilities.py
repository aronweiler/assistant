import re
import json

from langchain.schema.language_model import BaseLanguageModel


def parse_json(text: str, llm: BaseLanguageModel) -> dict:
    
    # Handle JSON code blocks (whole response)
    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3]
    
    # Handle JSON code blocks (inside other text within a response)
    pattern = re.compile(r"```(?:json)?\n(.*?)```", re.DOTALL)
    
    try:
        action_match = pattern.search(text)
        if action_match is not None:
            response = json.loads(action_match.group(1).strip(), strict=False)
            return response
        elif text.strip().startswith("{") and text.strip().endswith("}"):
            # Handles JSON responses that are not in code blocks
            return json.loads(text.strip(), strict=False)
        else:
            # Just return this as the answer??
            return {"final_answer": text}
    except Exception as e:
        if llm:
            llm_fixed_json = llm.predict(
                f"The following is badly formatted JSON, please fix it (only fix the JSON, do not otherwise modify the content):\n{text}\n\nAI: Sure, here is the fixed JSON (without modifying the content):\n"
            )
            return parse_json(llm_fixed_json, None)
        else:
            raise Exception(f"Could not parse LLM output: {text}") from e

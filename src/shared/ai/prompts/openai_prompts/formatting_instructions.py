FORMATTING_INSTRUCTIONS = """# Formatting Instructions
Please examine the following JSON schema, and ensure that your response adheres to this schema.  Additionally, please ensure that your response is a valid JSON object.

## JSON Schema
```json
{response_format}
```

Please note that this is the JSON schema for the response- not an example response.  Your response should be a JSON object that adheres to this schema.
{example_prompt}
# Response
AI: Sure, here is your valid JSON object adhering to the above schema:
"""

EXAMPLE_PROMPT = """
Here is an example response that should guide your output.

## Example Response

```json
{example}
```
"""
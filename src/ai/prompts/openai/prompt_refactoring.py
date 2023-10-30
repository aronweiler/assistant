ADDITIONAL_PROMPTS_TEMPLATE = """Please construct {additional_prompts} different prompts that I can use to search the loaded documents for content related to this prompt:

{user_query}

Return the prompts as a JSON list of strings.

Example: {{ "prompts": ["{{prompt_1}}", "{{prompt_2}}", "{{prompt_3}}"] }

AI: Sure, here is a JSON list of strings with {additional_prompts} different prompts that you can use to search the loaded documents for content related to this prompt:
"""
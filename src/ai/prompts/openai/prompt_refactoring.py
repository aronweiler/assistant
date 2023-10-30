ADDITIONAL_PROMPTS_TEMPLATE = """Please construct {additional_prompts} different prompts that I can use to search the loaded documents for content related to this prompt:

{user_query}

Return the prompts as a JSON list of strings.

Example: {{ "prompts": [{{"query": "full prompt", "semantic_similarity_query": "version of the prompt for semantic similarity matching", "keywords_list": ["keyword 1", "keyword 2", "etc."] }}] }}

AI: Sure, here is a JSON list of strings with {additional_prompts} different prompts that you can use to search the loaded documents for content related to this prompt:
"""
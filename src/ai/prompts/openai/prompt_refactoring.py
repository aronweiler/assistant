ADDITIONAL_PROMPTS_TEMPLATE = """Any previous conversation with the user is contained here. The chat history may contain context that you find useful to perform the following task.
--- CHAT HISTORY ---
{chat_history}
--- CHAT HISTORY ---

Please construct {additional_prompts} different prompts that I can use to search the loaded documents for content related to this prompt:

{user_query}



Return the prompts as a JSON list of strings inside of a Markdown code block.

Example: 
```json
{{ "prompts": [{{"query": "full prompt", "semantic_similarity_query": "version of the prompt for semantic similarity matching", "keywords_list": ["keyword 1", "keyword 2", "etc."] }}] }}
```

AI: Sure, here is a JSON list of strings with {additional_prompts} different prompts that you can use to search the loaded documents for content related to this prompt (I've put the JSON inside a ```json code``` block):
"""
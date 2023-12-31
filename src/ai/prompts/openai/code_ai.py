PLAN_STEPS_NO_TOOL_USE_TEMPLATE = """
{system_prompt}
You have access to the following code repository:
--- CODE REPOSITORY ---
{code_repository}
--- CODE REPOSITORY ---

--- RETRIEVED CONTEXT ---
{loaded_documents}
--- RETRIEVED CONTEXT ---

Your task is to dissect queries that are not directly answerable into clear, independent steps using the available tools. Each step should be self-contained and free of co-references.

In your response, adhere to the following structure:

1. **Preliminary Thoughts:** Outline your initial reasoning and decision-making process here (outside of the JSON blob). This will help us understand why you've chosen to use certain tools or provide a direct answer.

2. **Structured Response:** Present the actionable steps as a JSON array within a Markdown code block labeled as JSON (```json ... ```). For non-actionable direct responses, encapsulate the response in a similar JSON structure.

Here's an example for a query like "What's the weather like here?":
1. **Preliminary Thoughts:** I will use the 'get_location' tool to identify the user's current location, and then use the 'get_weather' tool to fetch the current weather for the user's location.

2. **Structured Response:**
```json
{{
  "steps": [
    {{"step_num": 1, "step_description": "Identify the user's current location", "tool": "get_location", "relies_on": []}},
    {{"step_num": 2, "step_description": "Fetch the current weather for the user's location", "tool": "get_weather", "relies_on": [1]}}
  ]
}}
```

For direct answers or conversational responses when no tool is applicable, format your response like this:
```json
{{
  "final_answer": "your direct or conversational response"
}}
```

Remember to consult the list of available tools and utilize them appropriately. Provide direct responses when no suitable tool exists.
--- AVAILABLE TOOLS ---
{available_tool_descriptions}
--- AVAILABLE TOOLS ---

Consider the chat history for additional context.
--- CHAT HISTORY ---
{chat_history}
--- CHAT HISTORY ---

Review the user's query to decide on a direct answer or a systematic breakdown.
--- USER QUERY ---
{user_query}
--- USER QUERY ---

It is crucial to ensure the clarity of each step and to eliminate any co-references.

Key Points to Remember:
- Use only the tools provided.
- Resolve all co-references to make each step executable independently.
- Encapsulate responses in a Markdown code block marked as JSON.
- Confirm the syntax of the JSON structure before finalizing your response.

If you are ready to present your structured response, proceed below. If not, please provide more detail in your Preliminary Thoughts.

AI: Sure, here are my thoughts and my response in JSON (inside a markdown ```json ``` code block):
"""
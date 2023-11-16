PLAN_STEPS_NO_TOOL_USE_TEMPLATE = """
{system_prompt}
Please start by reviewing the provided documents, focusing on their relevance to the tools at your disposal for task completion.
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

Your task is to dissect queries that are not directly answerable into clear, independent steps using the available tools. Each step should be self-contained and free of co-references.

In your response, adhere to the following structure:

1. **Preliminary Thoughts:** Outline your initial reasoning and decision-making process here. This will help us understand why you've chosen to use certain tools or provide a direct answer.

2. **Structured Response:** Present the actionable steps as a JSON array within a Markdown code block labeled as JSON. For non-actionable direct responses, encapsulate the response in a similar JSON structure.

Here's an example for a query like "What's the weather like here?":
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

ANSWER_PROMPT_TEMPLATE = """You are the final AI in a sequence of AIs that have been assisting a user with their inquiry. Your predecessors have compiled all the necessary information, and your task is to provide a definitive answer. The user's query and all relevant context have been outlined below.

User's Query:
{user_query}

Chat History for Context:
--- CHAT HISTORY ---
{chat_history}
--- END OF CHAT HISTORY ---

Helpful Context for Answering:
--- HELPFUL CONTEXT ---
{helpful_context}
--- END OF HELPFUL CONTEXT ---

Please provide your response in JSON format. If the query cannot be answered with the provided information, use the following structure:

```json
{{
  "failure": "Specific reason for the inability to answer the user's query with the given information."
}}
```

If the query can be answered, format your response as follows:

```json
{{
  "answer": "Your detailed and cited answer in Markdown format. Ensure to escape any characters that need to be escaped in JSON strings."
}}
```

Consider the chat history and helpful context carefully to formulate a comprehensive response to the user's query. Remember to format your answer in a visually pleasing manner, suitable for Markdown display, and adhere to JSON formatting conventions.

AI: Sure, here is my response in JSON (inside a markdown ```json ``` code block):
"""

TOOL_USE_TEMPLATE = """{system_prompt}

Your task is to create a JSON structure formatted as a Markdown code block. This JSON will define a call to a specific tool based on the details provided below:

Documents currently loaded (note each document's ID):
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

Previous user interactions:
--- CHAT HISTORY ---
{chat_history}
--- CHAT HISTORY ---

Additional context for the tool's use:
--- HELPFUL CONTEXT ---
{helpful_context}
--- HELPFUL CONTEXT ---

Details of the '{tool_name}' tool to be used:
--- TOOL DETAILS ---
{tool_details}
--- TOOL DETAILS ---

Pay close attention to the required arguments for this tool, and make sure to include them in the JSON output.

I want you to use the '{tool_name}' tool in order to do the following:
--- TOOL USE DESCRIPTION ---
{tool_use_description}
--- TOOL USE DESCRIPTION ---

Ensure the JSON includes all required arguments for '{tool_name}'. Format your response as follows:

```json
{{
  "tool_use_description": "describe_tool_use",
  "tool": "tool_name",
  "tool_args": {{
    "arg1_name": "arg1_value",
    "arg2_name": "arg2_value",
    ...
  }}
}}
```

For instance, using the 'get_weather' tool with arguments 'location' and 'date':
```json
{{
  "tool_use_description": "Retrieve weather information for a specific location and date",
  "tool": "get_weather",
  "tool_args": {{
    "location": "New York, NY",
    "date": "2021-01-01"
  }}
}}
```

Incorporate relevant details from the loaded documents or helpful context as needed. For example, a required file ID should come from the loaded documents.

Here's the user's query for context:
--- USER QUERY ---
{user_query}
--- USER QUERY ---

Please take your time to consider all the information before constructing the JSON.

AI: Sure! Here is the tool call in JSON (inside a Markdown ```json code block):
"""

TOOL_USE_RETRY_TEMPLATE = """{system_prompt}

I'm giving you a very important job. Your job is to construct a JSON blob that represents a tool call given the following information.

You have access to the following loaded documents (take note of the ID of each document):
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

Any previous conversation with the user is contained here. The chat history may contain context that you find useful to answer the current query.
--- CHAT HISTORY ---
{chat_history}
--- CHAT HISTORY ---

Please construct a new tool call that uses the one of the following tools.  The tool call should be different han the previous tool call.
--- AVAILABLE TOOLS ---
{available_tool_descriptions}
--- AVAILABLE TOOLS ---

Pay close attention to the required arguments for the chosen tool, and make sure to include them in the JSON output.

The goal is to attempt to retry the previous failed tool calls with a modified tool call that uses a different tool or the same tool with different arguments, in order to get better results.  

Your output should follow this JSON format:

```json
{{
  "tool_use_description": "Describe the use of this tool", "tool": "tool name", "tool_args": {{"arg 1 name": "arg 1 value", "arg 2 name": "arg 2 value", ...}}
}}
```

For example, if the tool is 'get_weather', and the tool arguments are 'location' and 'date', your response would look something like this:
```json
{{
  "step_description": "Get the weather at the user's location", "tool": "get_weather", "tool_args": {{"location": "New York, NY", "date": "2021-01-01"}}
}}
```

The loaded documents and the previous tool calls contain additional information that should inform your tool use.  For example, if the tool arguments require a file ID, then you should use the file ID of a loaded document. The previous tool call contains information on how the tool was called the last time- use this to make sure you call the tool in a different manner this time.

The following is the original user query we're trying to answer, use this to inform your tool use:
{user_query}

Here are the previous tool calls that were made:
----
{previous_tool_attempts}
----

Take a deep breath and examine the previous tool calls carefully.  

Think about the previous tool calls, take a step back, and construct a new tool call that attempts to answer the user's query, but with different or rephrased arguments than the previous tool calls.  Be creative in your approach, and try to think of a different way to use the tool to answer the user's query.

AI: Sure! I will think about this carefully.  I've taken a step back, and will approach this problem in a different way.  

I will use markdown and provide my thoughts below before providing the remainder the response in JSON (inside a ```json code``` block):
"""

SYSTEM_TEMPLATE = """You are my personal assistant.  It is your job to help me with whatever I need.  You are detail oriented, and methodical.  

Here is some helpful system information:
{system_information}"""
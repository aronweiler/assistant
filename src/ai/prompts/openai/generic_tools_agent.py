PLAN_STEPS_NO_TOOL_USE_TEMPLATE = """{system_prompt}

You have access the following tools that you can use by returning the appropriately formatted JSON. Don't make up tools, only ever use the tools that are listed here. If a query does not require the use of a tool (such as when it is conversational, or you know the answer), you can return a final_answer to the user instead.  If there are no tools available, or if none of the available tools suit your purpose, you should give a final_answer instead of using a tool that does not fit the purpose.

--- AVAILABLE TOOLS ---
{available_tool_descriptions}
--- AVAILABLE TOOLS ---

The loaded documents that you have access to are below.  Pay close attention to the Class of document it is.  Some tools can only be used with certain classes of documents.
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

Any previous conversation with the user is contained here. The chat history may contain context that you find useful to answer the current query.
--- CHAT HISTORY ---
{chat_history}
--- CHAT HISTORY ---

When the user's query cannot be answered directly, decompose the user's query into stand-alone steps that use the available tools in order to answer the user's query.  Make sure that each step contains enough information to be acted upon on it's own.  Do this by resolving coreferences, and providing any additional context that may be needed to answer the user's query in each step.

All responses are JSON blobs with the following format:
```json
{{
  "steps": [
    {{"step_num": <<step number>>, "step_description": "<<describe the step in detail here>>", "tool": "<<tool name (one of the available tools)>>", "relies_on": [<<list other step IDs this step relies on, if any>>]}},
    ...
  ]
}}

For example, if the user's query is "What's the weather like here?", you might split this into two steps- getting the user's location, and then getting the weather for that location.  Your response would look like this:
```json
{{
  "steps": [
    {{"step_num": 1, "step_description": "Get the user's current location", "tool": "get_location", "relies_on": []}},
    {{"step_num": 2, "step_description": "Get the weather for the user's location", "tool": "get_weather", "relies_on": [1]}}
  ]
}}
```

Please take note of the "relies_on" field in the JSON output.  This field is used to indicate which previous steps this step relies on.  If a step does not rely on any previous steps, this field should be an empty list.  If a step relies on a previous step, the "relies_on" field should contain a list of the step numbers that this step relies on.  For example, if step 3 relies on steps 1 and 2, the "relies_on" field for step 3 should be [1, 2].

If you can answer the user's query directly, or the user's query is just conversational in nature, you should respond with the following JSON blob:
```json
{{
  "final_answer": "<<your complete answer to the query, or your response to a conversation>>"
}}
```

Now take a deep breath, and read the user's query very carefully. I need you to decide whether to answer the user's query directly, or decompose a list of steps.

--- USER QUERY ---
{user_query}
--- USER QUERY ---

AI: Sure, I will decide whether to answer the user directly, or whether to provide a list of steps. Here is my response (in JSON format):
"""

ANSWER_PROMPT_TEMPLATE = """You are the final AI in a chain of AIs that have been working on a user's query.  The other AIs have gathered enough information for you to be able to answer the query.  Now, I would like you to answer the user's query for me using the information I provide here.

The user's query is: 
{user_query}

This helpful context contains all of the information you will require to answer the query, pay attention to it carefully.
--- HELPFUL CONTEXT ---
{helpful_context}
--- HELPFUL CONTEXT ---

If you cannot answer the user's query, please return a JSON blob with the following format:
```json
{{
  "failure": "<<explain precisely why you cannot answer the user's query with the information in the helpful context>>"
}}
```

If you can answer the user's query, please return a JSON blob with the following format:
```json
{{
  "answer": "<<markdown formatted complete answer here (remember to escape anything required to be used in a JSON string).  take a deep breath here and make sure you carefully enter all of the details from the helpful context that make up this answer.  Be very detail oriented, and quote verbatim where possible.  If there are sources in the helpful context, make sure to include them here.>>"
}}
```

Use the helpful context above to answer the user's query, which is:
{user_query}

AI: Sure! Here is my response (in JSON format):
"""

TOOL_USE_TEMPLATE = """{system_prompt}

I'm giving you a very important job. Your job is to construct a JSON blob that represents a tool call given the following information.

You have access to the following loaded documents (take note of the ID of each document):
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

The following helpful context may contain additional information that should inform your tool use:
--- HELPFUL CONTEXT ---
{helpful_context}
--- HELPFUL CONTEXT ---

Please construct a tool call that uses the '{tool_name}' tool.  The '{tool_name}' tool has the following details:
--- TOOL DETAILS ---
{tool_details}
--- TOOL DETAILS ---

Pay close attention to the required arguments for this tool, and make sure to include them in the JSON output.

I want you to use the '{tool_name}' tool in order to do the following:
--- TOOL USE DESCRIPTION ---
{tool_use_description}
--- TOOL USE DESCRIPTION ---

Your output should follow this JSON format:

```json
{{
  "tool_use_description": "<<Describe the use of this tool>>", "tool": "<<tool name>>", "tool_args": {{"<<arg 1 name>>": "<<arg 1 value>>", "<<arg 2 name>>": "<<arg 2 value>>", ...}}
}}
```

For example, if the tool is 'get_weather', and the tool arguments are 'location' and 'date', your response would look something like this:
```json
{{
  "step_description": "Get the weather at the user's location", "tool": "get_weather", "tool_args": {{"location": "New York, NY", "date": "2021-01-01"}}
}}
```

The loaded documents and the helpful context may contain additional information that should inform your tool use.  For example, if the tool arguments require a file ID, then you should use the file ID of a loaded document, or if the tool arguments require a location you should use the location from the helpful context, etc.

The following was the original user query:
{user_query}

Take a deep breath, and think this through.  Make sure to resolve any coreferences in the steps, so that each step can be interpreted on its own.

AI: Sure! Here is my response (in JSON format):
"""

TOOL_USE_RETRY_TEMPLATE = """{system_prompt}

I'm giving you a very important job. Your job is to construct a JSON blob that represents a tool call given the following information.

You have access to the following loaded documents (take note of the ID of each document):
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

Please construct a modified tool call that uses the '{tool_name}' tool, but with different arguments, or rephrased content.  
The '{tool_name}' tool has the following details:
--- TOOL DETAILS ---
{tool_details}
--- TOOL DETAILS ---

Pay close attention to the required arguments for this tool, and make sure to include them in the JSON output.

The goal is to attempt to retry the previous failed tool calls with a modified tool call that uses the '{tool_name}' tool, but with different arguments, or rephrased content, in order to get better results.  

Your output should follow this JSON format:

```json
{{
  "tool_use_description": "<<Describe the use of this tool>>", "tool": "<<tool name>>", "tool_args": {{"<<arg 1 name>>": "<<arg 1 value>>", "<<arg 2 name>>": "<<arg 2 value>>", ...}}
}}
```

For example, if the tool is 'get_weather', and the tool arguments are 'location' and 'date', your response would look something like this:
```json
{{
  "step_description": "Get the weather at the user's location", "tool": "get_weather", "tool_args": {{"location": "New York, NY", "date": "2021-01-01"}}
}}
```

The loaded documents and the previous tool call contain additional information that should inform your tool use.  For example, if the tool arguments require a file ID, then you should use the file ID of a loaded document. The previous tool call contains information on how the tool was called the last time- use this to make sure you call the tool in a different manner this time.

The following is the original user query we're trying to answer, use this to inform your tool use:
{user_query}

Here are the previous tool calls that were made:
----
{previous_tool_attempts}
----

Take a deep breath and examine the previous tool calls carefully.  

Think about the previous tool calls, and construct a new tool call that attempts to answer the user's query, but with different or rephrased arguments than the previous tool calls.  Be creative in your approach, and try to think of a different way to use the tool to answer the user's query.

AI: Sure! I will think about this carefully.  Here is my response containing a modified tool call that is different than the previous tool calls (in JSON format):
"""

SYSTEM_TEMPLATE = """I'd like you to act as a personal assistant. It's important that you provide detailed and accurate assistance to me. 

As my personal assistant, I expect you to be attentive, proactive, and reliable. You should be ready to help me with any questions, provide information, or engage in friendly conversation. Let's work together to make my day easier and more enjoyable!

I want you to adjust your responses to match my preferred personality. I will provide personality descriptors below to indicate how you should customize your response style. Whether I want you to sound witty, professional, or somewhere in between, I expect you to adapt accordingly.

--- PERSONALITY DESCRIPTORS ---
{personality_descriptors}
--- PERSONALITY DESCRIPTORS ---

Here is some helpful system information:
{system_information}"""
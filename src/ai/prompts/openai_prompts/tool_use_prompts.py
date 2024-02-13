TOOL_USE_TEMPLATE = """{system_prompt}

Your task is to create a JSON structure formatted as a Markdown code block. This JSON will define a call to a specific tool based on the details provided below:
{loaded_documents_prompt}
{selected_repository_prompt}
{previous_tool_calls_prompt}
{chat_history_prompt}
Additional context for the tool's use (please note: the user will never see this context):
--- HELPFUL CONTEXT ---
{helpful_context}
--- HELPFUL CONTEXT ---

Details of the `{tool_name}` tool you will be constructing a call for:
--- TOOL DETAILS ---
{tool_details}
--- TOOL DETAILS ---

Pay close attention to the required arguments for this tool, and make sure to include them in the JSON output.  Do not use placeholders for values- only use actual values.  If you don't have a value for a required argument, then you cannot use the tool.

I want you to use the `{tool_name}` tool in order to do the following:
--- TOOL USE DESCRIPTION ---
{tool_use_description}
--- TOOL USE DESCRIPTION ---

Ensure the tool JSON you provide includes all required arguments for `{tool_name}`. 

Incorporate relevant details from the loaded documents or helpful context as needed. 

Here's the user's query for context:
--- USER QUERY ---
{user_query}
--- USER QUERY ---

Please take your time to consider all the information before constructing your response.

Now... take a deep breath and relax! I have complete confidence in your abilities."""

TOOL_USE_RETRY_TEMPLATE = """{system_prompt}
{loaded_documents_prompt}
{selected_repository_prompt}
{previous_tool_calls_prompt}
{chat_history_prompt}

I'm giving you a very important job. Your job is to construct a JSON blob that represents a tool call given the following information.

Please construct a new tool call that uses the one of the following tools.  The goal is to attempt to retry the previous failed tool call(s) with a modified tool call that uses a different tool or the same tool with different arguments, in order to get better results.
--- AVAILABLE TOOLS ---
{available_tool_descriptions}
--- AVAILABLE TOOLS ---

Pay close attention to the required arguments for the chosen tool, and make sure to include them in the JSON output.

The goal is to attempt to retry the previous failed tool calls with a modified tool call that uses a different tool or the same tool with different arguments, in order to get better results.  

The following is the original user query we're trying to answer, use this to inform your tool use:
{user_query}

Here are the previous tool calls that were made on this user query:
----
{failed_tool_attempts}
----

Take a deep breath and examine the previous tool calls carefully.  

Think about the previous tool calls, take a step back, and construct a new tool call that attempts to answer the user's query, but with different or rephrased arguments than the previous tool calls.  Be creative in your approach, and try to think of a different way to use the tool to answer the user's query."""

ADDITIONAL_TOOL_USE_TEMPLATE = """{system_prompt}
{loaded_documents_prompt}
{selected_repository_prompt}
{previous_tool_calls_prompt}
{chat_history_prompt}
Another AI has constructed the following tool use JSON object for the '{tool_name}' tool in an attempt to answer the user's query:
```json
{initial_tool_use}
```

Your task is to construct {additional_tool_uses} tool use JSON objects for the '{tool_name}' with various (different) arguments in an attempt to answer this query: 

Query: {user_query}

The tool use description for the '{tool_name}' tool is:
{tool_use_description}

Please be creative and attempt to construct different tool use JSON objects in order to answer the query.

Additionally, please ensure the tool JSON you provide includes all required arguments for `{tool_name}`."""

PREVIOUS_TOOL_CALLS_TEMPLATE = """
The following are previous tool calls that were made in this conversation.  If you are considering constructing a new tool call, you should consider the previous tool calls to ensure you are not repeating a tool call that has already been made.  

IMPORTANT! When using the results from previous tool calls, make sure to CAREFULLY examine the previous call to ensure that it exactly matches the tool call you would construct, otherwise you may be using the wrong results.  This includes file name searches, code pulls, etc.  If you are unsure, please construct a NEW tool call instead of using the results from a previous tool call.
--- PREVIOUS TOOL CALLS ---
{previous_tool_calls}
--- PREVIOUS TOOL CALLS ---

Now... take a deep breath and relax! I have complete confidence in your abilities."""

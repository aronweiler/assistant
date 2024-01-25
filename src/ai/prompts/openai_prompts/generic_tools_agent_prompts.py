PLAN_STEPS_NO_TOOL_USE_TEMPLATE = """
{system_prompt}
{loaded_documents_prompt}
{selected_repository_prompt}
{previous_tool_calls_prompt}
Your task is to dissect queries that are not directly answerable into clear, independent steps using the available tools. Each step should be self-contained and free of co-references.

In your response, please give your preliminary thoughts on the query and outline your initial reasoning and decision-making process, and give either a direct answer or a systematic breakdown of the steps to be taken. If you choose to give a direct answer, please provide a clear explanation of your reasoning. If you choose to give a systematic breakdown, please provide a clear explanation of each step and how it relates to the user's query.

Remember to consult the list of available tools and utilize them appropriately. Provide direct responses when no suitable tool exists.
--- AVAILABLE TOOLS ---
{available_tool_descriptions}
--- AVAILABLE TOOLS ---
{chat_history_prompt}
Review the user's query to decide on a direct answer or a systematic breakdown.
--- USER QUERY ---
{user_query}
--- USER QUERY ---

It is crucial to ensure the clarity of each step and to eliminate any co-references.

Key Points to Remember:
- Use only the tools provided. Do not use placeholders for tools that do not exist.
- Resolve all co-references to make each step executable independently.
- Confirm the syntax of the JSON structure before finalizing your response."""

LOADED_DOCUMENTS_TEMPLATE = """
Please start by reviewing the provided documents, focusing on their relevance to the tools at your disposal for task completion.
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---
"""

SELECTED_REPO_TEMPLATE = """
The following is a code repository that the user has selected for this conversation.
--- SELECTED REPOSITORY ---
{selected_repository}
--- SELECTED REPOSITORY ---
"""

CHAT_HISTORY_TEMPLATE = """
Consider the chat history for additional context.
--- CHAT HISTORY ---
{chat_history}
--- CHAT HISTORY ---
"""

PREVIOUS_TOOL_CALLS_TEMPLATE = """
The following are previous tool calls that were made in this conversation.  If you are considering constructing a new tool call, you should consider the previous tool calls to ensure you are not repeating a tool call that has already been made.
--- PREVIOUS TOOL CALLS ---
{previous_tool_calls}
--- PREVIOUS TOOL CALLS ---
"""

ANSWER_PROMPT_TEMPLATE = """You are the final AI in a sequence of AIs that have been assisting a user with their inquiry. Your predecessors have compiled all the necessary information, and your task is to provide a definitive answer. The user's query and all relevant context have been outlined below.
{chat_history}
User's Query:
{user_query}


Helpful Context for Answering:
--- HELPFUL CONTEXT ---
{helpful_context}
--- END OF HELPFUL CONTEXT ---

Consider the chat history and helpful context carefully to formulate a comprehensive response to the user's query. """

TOOL_USE_TEMPLATE = """{system_prompt}

Your task is to create a JSON structure formatted as a Markdown code block. This JSON will define a call to a specific tool based on the details provided below:{loaded_documents_prompt}
{selected_repository_prompt}
{previous_tool_calls_prompt}
{chat_history_prompt}
Additional context for the tool's use:
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

Please take your time to consider all the information before constructing your response."""

TOOL_USE_RETRY_TEMPLATE = """{system_prompt}

I'm giving you a very important job. Your job is to construct a JSON blob that represents a tool call given the following information.
{loaded_documents_prompt}
{selected_repository_prompt}
{previous_tool_calls_prompt}
{chat_history_prompt}

Please construct a new tool call that uses the one of the following tools.  The tool call should be different han the previous tool call.
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

SYSTEM_TEMPLATE = """You are my personal assistant.  It is your job to help me with whatever I need.  You are detail oriented, and methodical.  

Here is some helpful system information:
{system_information}"""

EVALUATION_TEMPLATE = """{chat_history_prompt}

Please evaluate the following information and provide an evaluation and score for the previous AI's response to the user's query.  

User's Original Query:
{user_query}

Previous AI's Response:
{previous_ai_response}

Tools Used by Previous AI (including results from tool calls):
{tool_history}

Tools that were available to the previous AI:
{available_tool_descriptions}

{loaded_documents_prompt}
{selected_repository_prompt}

Based on this information, please provide an evaluation of the previous AI's response in terms of completeness and correctness, and score the previous AI's response, including which tools it chose to use on a scale from 0.0 to 1.0."""
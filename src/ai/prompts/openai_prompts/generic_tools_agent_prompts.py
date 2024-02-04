PLAN_STEPS_NO_TOOL_USE_TEMPLATE = """
{system_prompt}
{user_settings_prompt}
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

SETTINGS_HEADERS_TEMPLATE = """
The following is a list of setting names that are available for you to retrieve / set.
--- SETTINGS ---
{settings_headers}
--- SETTINGS ---
"""

ANSWER_PROMPT_TEMPLATE = """I need your help to answer the following question.  Please review the chat history and context carefully to formulate a comprehensive response to the user's query.

## Context:
*This context contains any previous tool call results that have been made in the context of the current query from the user.*
{helpful_context}

## Chat History:
{chat_history}

## User's Query:
{user_query}

## Instructions:
Please carefully consider the chat history and context provided here to formulate a comprehensive response to the user's query.  If you are unable to answer the user's query, please provide a clear explanation of why you are unable to answer the query."""

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
{user_settings_prompt}

Based on this information, please provide an evaluation of the previous AI's response in terms of completeness and correctness, and score the previous AI's response, including which tools it chose to use on a scale from 0.0 to 1.0."""

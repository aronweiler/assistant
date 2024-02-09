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
- Confirm the syntax of the JSON structure before finalizing your response.
{rephrase_answer_instructions_prompt}"""

REPHRASE_ANSWER_INSTRUCTIONS_TEMPLATE = """
Finally, please rephrase both your preliminary thoughts, and final answer (not the steps) to follow the instructions below:
{rephrase_answer_instructions}
"""

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
The following is a list of your settings that are available for you to retrieve / set.  When a user asks you about a setting, or tells you to change a setting, they are referring to this section.
Use the settings tool(s) to interact with these settings.
--- SETTINGS ---
{settings_headers}
--- SETTINGS ---
"""

ANSWER_PROMPT_TEMPLATE = """I need your help to answer the following question.  Please review the chat history and context carefully to formulate a comprehensive response to the user's query.

## Internal Context:
*This internal context contains any previous tool call results that have been made for the current query from the user.  Note: The user will never see this information!  If you are constructing an answer that uses this data, be sure to repeat it in your response, don't ever refer to this information in your answer (because the user will never see it).*
{helpful_context}

## Chat History:
{chat_history}

## User's Query:
{user_query}

## Instructions:
Please carefully consider the chat history and context provided here to formulate a comprehensive response to the user's query.  If you are unable to answer the user's query, please provide a clear explanation of why you are unable to answer the query.
{rephrase_answer_instructions_prompt}"""

SYSTEM_TEMPLATE = """You are my personal assistant.  It is your job to help me with whatever I need.  You are detail oriented, and methodical.  

Here is some helpful system information:
{system_information}"""

EVALUATION_TEMPLATE = """{chat_history_prompt}

Please look closely at the following information and provide an evaluation and score for the previous AI's response to the user's query.  

## Tools Used by Previous AI to resolve the user's query (including results from tool calls):
{tool_history}

## Tools that were available to the previous AI:
{available_tool_descriptions}

{loaded_documents_prompt}
{selected_repository_prompt}
{user_settings_prompt}

# User's Original Query:
{user_query}

# Previous AI's Response:
{previous_ai_response}

Based on this information, please provide an evaluation of how well the previous AI's response resolves the user's query and score the previous AI's response on a scale from 0.0 to 1.0.

Make sure you look at attributes such as:
- Completeness - Did the previous AI fully resolve the user's query?
- Correctness - Was the previous AI's response as correct as it could be?
- Clarity - Was the previous AI's response clear and easy to understand?
- Relevance - Was the previous AI's response relevant to the user's query?
- Use of available tools - Did the previous AI use the available tools effectively?"""

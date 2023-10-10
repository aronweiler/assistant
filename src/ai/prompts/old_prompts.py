
SPLIT_STEPS_TEMPLATE = """{system_prompt}

You have access the following tools that you can use by returning the appropriately formatted JSON. Don't make up tools, only ever use the tools that are listed here. If a query does not require the use of a tool (such as when you know the answer, or the answer exists in this context), you can return an answer to the user instead.  If there are no tools available, or if none of the available tools suit your purpose, you should return an answer to the user instead of using a tool.
--- AVAILABLE TOOLS ---
Name: final_answer
Description: Gives a final answer to the user.
Additional Instructions: Use this tool when you have all of the information necessary to answer the user's query.  If you don't have all of the information necessary to answer the user's query, you should use one of the other tools instead.
Args (name, type, optional/required):
  user_query, str, required
	answer, str, required
---
{available_tools}
--- AVAILABLE TOOLS ---
Pay close attention to the required arguments for each tool, and make sure to include them in the JSON output.

The loaded documents that you have access to are below.
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

Any previous conversation with the user is contained here. The chat history may contain context that you find useful to answer the current query.
--- CHAT HISTORY ---
{chat_history}
--- CHAT HISTORY ---
{previous_steps}
--- USER QUERY ---
{user_query}
--- USER QUERY ---

Read the user's query carefully. If you cannot fully answer the user's query, break the user's query up into stand-alone steps using the available tools that can be used to answer the user's query.

All responses are JSON blobs with the following format:
```json
{{
  "step_description": "<<describe the step here>>", "tool": "<<tool name (one of the available tools)>>", "tool_args": {{"arg name": "arg value", "another arg name": "another arg value"}}
}}
```

For example, if the user's query is "What's the weather like here?", you might split this into two steps- getting the user's location, and then getting the weather for that location.  Assuming the get_location tool takes no arguments, your response would look like this (only returning the first step: get_location):
```json
{{
  "step_description": "Get the user's current location", "tool": "get_location"
}}
```

If the user's location is already known to you, you would respond with the get_weather step:
```json
{{
  "step_description": "Get the weather at the user's location", "tool": "get_weather", "tool_args": {{"location": "New York, NY"}}
}}
```

If the user's query can be fully answered with the available information (i.e. you have all of the information necessary to answer the query, either from the various context in this prompt or previous steps taken), respond with the following JSON blob:
```json
{{
  "step_description": "Answer to the user's query", "tool": "final_answer", "tool_args": {{"user_query": "<<original user's query>>", "answer": "<<your complete answer here>>"}}
}}
```

It is important that you only respond with an answer when the user's query is FULLY resolved (i.e. if it is a multi-part query, all parts must be answered).  If you can't answer the user's query, you should respond with a new step instead (make sure you aren't repeating steps).

AI: Sure, no problem.  I will look carefully at the user's query, any helpful context, chat history, system information, loaded documents, and all of the other context provided here. I will respond with either an answer (assuming the user's query can be fully answered with the available data), or another step for you to take in order to provide me with more information.  

If I can fully answer the user's query with the available information, I will do so.  If I need to continue to provide you with steps to fully answer the user's query, I will do that.
{answered_steps_hint}
I've made sure that I am not repeating earlier steps I took, and here is my response (in JSON format):
"""

# If the user's query cannot be fully answered with t he available context, I want you to respond with a single step that represents the next logical step in resolving the user's query.  Make sure not to give me back an answer unless the user's query is resolved.
# First, I will think this through step-by-step.  Then I will return a JSON blob response.  My first thought is:
# Do I have enough information to resolve the user's query?
# """

AGENT_PROMPT_TEMPLATE = """{system_prompt}

You have access the following tools that you can use by returning the appropriately formatted JSON.  Don't make up tools, only ever use the tools that are listed here. If a query does not require the use of a tool, you can return a final answer to the user instead.  If there are no tools available, or if none of the available tools suit your purpose, you can return a final answer to the user instead.
--- AVAILABLE TOOLS ---
{available_tools}
--- AVAILABLE TOOLS ---
Pay close attention to the required arguments for each tool, and make sure to include them in the JSON output.

The format of your response should always follow these formatting guidelines:
--- RESPONSE FORMATTING ---
{response_formatting_instructions}
--- RESPONSE FORMATTING ---

The loaded documents that you have access to are below.  Pay attention to the IDs of these loaded documents, you will need to use these IDs when using the tools.
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

Any previous conversations with the user are contained here. The chat history may contain context that you find useful to answer a current query.
--- CHAT HISTORY ---
{chat_history}
--- CHAT HISTORY ---

--- INSTRUCTIONS ---
{agent_instructions}
--- INSTRUCTIONS ---

{examples}

--- USER QUERY ---
{user_query}
--- USER QUERY ---

Begin.  Remember to follow the instructions carefully, as well as making sure you adhere to the JSON output format.  Pay close attention to the required arguments for each tool, and make sure to include them in the JSON output.  Only respond with a single JSON action at a time.

Thought: Given the context here, can I provide the user with a final answer? """

AGENT_ROUND_N_TEMPLATE = """{previous_work}

Observation: {observation}

--- REMINDERS ---
Only respond with one action at a time.  We will run this loop many times if necessary. 

You must ultimately respond with a JSON blob that follows the expected format after you have completed your thought (and optionally your steps). If you are using a tool, make sure to double-check the required arguments, and be sure you have included them in the JSON.  If you are returning a final answer, make sure to include it in the JSON.

Your valid `action` values are one of the following: "final_answer" {tool_names}
--- REMINDERS ---

Thought: Given the context here, can I provide the user with a final answer, or are there tools that I can call """

RESPONSE_FORMATTING_TEMPLATE = """All responses should be in the following JSON format:
```json
{
  "action": $ACTION,
  "action_input": $ACTION_INPUT
}

Where $ACTION is the name of the tool you want to use, and $ACTION_INPUT is the input to that tool.  For example, if you want to use the hypothetical "search_internet" tool that takes a query argument, and you want to search for the word "cat", you would return the following JSON:
```json
{
  "action": "search_internet",
  "action_input": {
    "query": "cat"
  }
}
```

When it is not appropriate to use a tool, or you want to return a final answer to the user when their query is fully satisfied, use the following format:
```json
{
  "action": "final_answer",
  "action_input": "<<Your final answer goes here>>"
}
```

Only ever respond with one JSON blob in your response.  We will run this loop several times if necessary."""

AGENT_INSTRUCTIONS_TEMPLATE = """To answer the user's query, you should follow the "Thought / Steps / Action / Observation" pattern outlined below.  This pattern can repeat over many iterations, such as when a user has a multi-part query or a query that requires multiple steps or tools to answer.

Thought: Given the various context provided here (loaded documents, chat history, previous work, etc.), or your own internal knowledge, do you have enough information to answer the user's query?  You will think through the user's query step by step, take into account any previously taken steps, and place plans for subsequent steps here.

Steps: This is where you will break down the user's query into the steps that you need to take in order to arrive at the final answer.  Plan out all of the steps necessary to answer the user's query.  These steps should either be your plan to use a tool or return a final answer.

Action: This is where you will provide the JSON formatted action to take.  This action could be the use of a tool, or a "final_answer".  If you are using a tool, make sure to double-check the required arguments, and be sure you have included them in the JSON. Only include one single JSON action in your response.  If the completion of your thought requires multiple steps, we will repeat this process.

Observation: This is where you will be provided the output of any tool calls that you have requested in the Action above.  Use details here in Observation to help answer the user's query."""

STAND_ALONE_EXAMPLE = """--- BEGIN TRAINING DATA EXAMPLE ---
User Query: If I have 4 apples, and I give three to my friend Tommy, how many apples do I have?

Thought: Given the context here, or my own training, can I provide the user with a final answer? Yes, this is a simple math problem that I can solve without the use of external tools. I can answer the user's query without any additional context. The user started with 4 apples, and gave 3 to Tommy.  The user wants to know how many apples they have left.  4 minus 3 is 1, so the user has 1 apple left.

Steps:
1. Subtract 3 from 4, and provide the final answer to the user.

Action:
```json
{
  "action": "final_answer",
  "action_input": "You started with four apples, and gave three to your friend Tommy.  You have one apple left."
}
```
--- END TRAINING DATA EXAMPLE ---"""

SINGLE_HOP_EXAMPLE = """--- BEGIN SINGLE-HOP EXAMPLE ---
User Query: How many years of experience does John Smith have working on medical devices?

Thought: Given the context here, or my own training, can I provide the user with a final answer? No, I don't have enough context. I need to find out how many years of experience John has working on medical devices. Are there loaded documents that can help me?  Yes, it looks like John's resume is loaded under the name "john-smith-resume.pdf".  I will use the search_document tool to search for "medical devices" in "john-smith-resume.pdf", which has the file_id of "99".  That should give me the information I need.

Steps:
1. I will use the search_document tool to search for John's experience with medical devices in the document with the file_id of "99"
2. I will and construct the final answer describing John's history of medical device experience, and return it to the user.

Action:
```json
{
  "action": "search_document",
  "action_input": {
    "query": "medical device",
    "target_file_id": "99"
  }
}
```

Observation: 
John worked at Boston Scientific on an insulin pump from 2002 until 2007.  He also worked at Medtronic on a pacemaker from 2007 until 2010.  

Thought: After evaluating the response from the search_document tool above (in the Observation), I have determined that I can answer the user's query. I don't need to plan out any more steps, so I will construct the final answer describing John's history of medical device experience using the context provided.

Steps:
1. Return the final answer to the user.

Action:
```json
{
  "action": "final_answer",
  "action_input": "According to my search of 'john-smith-resume.pdf', John worked on an insulin pump at Boston Scientific from 2002 until 2007, and then he worked at Medtronic on a pacemaker from 2007 until 2010. From these results, I can determine that John has 8 years of experience working on medical devices."
}
```
--- END SINGLE-HOP EXAMPLE ---"""

MULTI_HOP_EXAMPLE = """--- BEGIN MULTI-HOP EXAMPLE ---
User Query: Who is Leo DiCaprio's girlfriend? What is her current age raised to the 0.43 power?

Thought: Given the context here, or my own training, can I provide the user with a final answer? No, I don't have enough context. I need to find out who Leo DiCaprio's girlfriend is, what her age is, and then calculate her age raised to the 0.43 power. To do this, I will use the web_search tool to find the answer to who Leo DiCaprio's girlfriend is, then I will use the web_search tool again to find out what her age is.  After I have Leo DiCaprio's girlfriend's age, I will use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power.  

Steps:
1. Use the web_search tool to find the answer to who Leo DiCaprio's girlfriend is.
2. Use the web_search tool to find out what her age is.
3. Use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power.
4. Return the final answer of what Leo DiCaprio's girlfriend's age raised to the 0.43 power is to the user.

Action:
```json
{
  "action": "web_search",
  "action_input": {
    "query": "Who is Leo DiCaprio's girlfriend?"
  }
}
```
Observation: Leo DiCaprio's girlfriend is Vittoria Ceretti.

Thought: Given the context here, or my own training, can I provide the user with a final answer? No, I don't have enough context. I still need to find Vittoria Ceretti's age. I will use the web_search tool again to find out what her age is.  After I have Leo DiCaprio's girlfriend's age, I will use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power.  The required arguments for the web_search tool is the query.  The required arguments for the calculate_power tool is the number and the power. 

Steps:
1. Use the web_search tool to find out what Vittoria Ceretti's age is.
2. Use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power.
3. Return the final answer of what Leo DiCaprio's girlfriend's age raised to the 0.43 power is to the user.

Action:
```json
{
  "action": "web_search",
  "action_input": {
    "query": "What is Vittoria Ceretti's age?"
  }
}
```
Observation: Vittoria Ceretti is 25.

Thought: Given the context here, or my own training, can I provide the user with a final answer? No, I don't have enough context. I still need to calculate Vittoria Ceretti's age raised to the 0.43 power, I will use the calculate_power tool to calculate the answer to 25 raised to the 0.43 power.  

Steps:
1. Use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power.
2. Return the final answer of what Leo DiCaprio's girlfriend's age raised to the 0.43 power is to the user.

Action:
```json
{
  "action": "calculate_power",
  "action_input": {
    "number": 25,
    "power": 0.43
  }
}
```
Observation: 3.991298452658078

Thought: Given the context here, or my own training, can I provide the user with a final answer? Yes, I have used the web_search and calculate_power tools to arrive at the final answer to the user's query. Leo DiCaprio's girlfriend is Vittoria Ceretti, who is 25 years old. 25 raised to the 0.43 power is 3.991298452658078.

Steps:
1. Return the final answer of what Leo DiCaprio's girlfriend's age raised to the 0.43 power is to the user.

Action:
```json
{
  "action": "final_answer",
  "action_input": "Leo DiCaprio's girlfriend is Vittoria Ceretti, who is 25 years old. Her age raised to the 0.43 power is 3.991298452658078."
}
```
--- END MULTI-HOP EXAMPLE ---"""

OLDDDDDBETTER_AGENT_PROMPT_TEMPLATE = """{system_prompt}

You have been tasked with answering a user's query.  You have access the following tools that you can use by returning the appropriate JSON.

--- BEGIN AVAILABLE TOOLS ---
{tool_signatures}
--- END AVAILABLE TOOLS ---

To use a tool, return a JSON blob to that specifies a tool and its arguments by providing an `action` key, the value of which is the tool name, and an `action_input` key, the value of which is the tool's arguments (if any).

Valid `action` values are: "Final Answer" or {tool_names}

Provide only ONE action per $JSON_BLOB, formatted as shown:

--- BEGIN JSON BLOB FORMAT ---
```json
{{{{
  "action": $TOOL_NAME,
  "action_input": $INPUT
}}}}
```
--- END JSON BLOB FORMAT ---

Then, follow this format for your response:

Original User Input: <<Print the unmodified original user input>> 

Thought: <<Did any previous work answer the user's query? (answer this in your response) Think through the user's query step by step, take into account any previously taken steps, and place your plans for subsequent steps here. If your plans include the use of a tool, make sure to double-check the required arguments and list them here as well. Think carefully if you have enough information to answer the users query based on your own knowledge or previous work, and if so you can return the final answer.>>

Step 1: <<Describe the steps that you need to take in order to arrive at the final answer, including the required and optional arguments to any tools.>>
... (Make sure to mark steps as COMPLETE when they have been completed)
Step N: Return the final answer to the user.

Tool Query: <<When using a tool, you should consider the context of the user's query, and rephrase it (if necessary) to better use the chosen tool. This could mean modifying the query to be more concise, adding additional context, or splitting it into keywords.  Place that modified query here for reference.>>

Action:
```
$JSON_BLOB
```

Observation: <<The action result.  Usually this is the output of a previous tool call.  If you have previously used a tool, the output will be here>>

... (repeat Thought/Steps/Action/Observation loop as many times as necessary to get to the final answer- this is useful when a user has a multi-part query or a query that requires multiple steps or tools to answer)

When you arrive at the final answer to the query, the response format is:
```json
{{{{
  "action": "Final Answer",
  "action_input": "<<Your final response to the user>>"
}}}}
```

Consider the context provided in the chat history, loaded documents, and additional user information when deciding which tool to use:

--- CHAT HISTORY ---
{chat_history}
--- CHAT HISTORY ---

--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

Think this through step-by-step. Note the type of document (Document, Code, Spreadsheet, etc.), and be certain to use the right tool and arguments in the json blob.  Pay close attention to the tool descriptions!

--- FORMAT --- 
Action:
```json
$JSON_BLOB
```
--- FORMAT --- 

Sometimes a query can be answered in a single hop (e.g. query to a tool):
--- BEGIN SINGLE-HOP EXAMPLE ---
Original User Input: What kind of experience does John Smith have working on medical devices?

Thought: Did any of the previous steps give me enough data to answer the question?  No, there are no previous steps. I need to find out what kind of experience John has working on medical devices. To find an answer to this, I can search the loaded documents for information related to medical devices. Since it looks like John's resume is in the loaded documents, I will search the "john-smith-resume.pdf" (which has the file_id of '99') document for details about his experience in this field.  The required arguments are the query and the original user input.  The target_file_id argument is optional, but will allow me to refine my search to John's resume, so I will include that in the JSON blob as well.

The steps I need to follow are:
Step 1: Use the search_loaded_documents tool to search for John's experience with medical devices (The required arguments are 'query', 'original_user_input', the optional arguments are 'target_file_id')
Step 2: Return the final answer about John's medical device experience to the user.

Tool Query: medical devices

Action:
```json
{{
  "action": "search_loaded_documents",
  "action_input": {{
    "query": "medical devices",
    "original_user_input": "What kind of experience does John Smith have working on medical devices?",
    "target_file_id": "99"
  }}
}}
```
Observation: 
John has 5 years of experience working on medical devices.

Original User Input: What kind of experience does John Smith have working on medical devices?

Thought: Did any of the previous steps give me enough data to answer the question? Yes, John has 5 years of experience working on medical devices. I will return the final answer to the user.

The steps I need to follow are:
Step 1: COMPLETE
Step 2: Return the final answer about John's medical device experience to the user.

Action:
```json
{{
  "action": "Final Answer",
  "action_input": "John has 5 years of experience working on medical devices."
}}
```
--- END SINGLE-HOP EXAMPLE ---

Sometimes a query cannot be answered in a single hop, and requires multiple hops (e.g. multiple queries to a tool, or other intermediate steps taken by you):
--- BEGIN MULTI-HOP EXAMPLE ---
Original User Input: Who is Leo DiCaprio's girlfriend? What is her current age raised to the 0.43 power?

Thought: Did any of the previous steps give me enough data to answer the question? No, there are no previous steps. I need to find out who Leo DiCaprio's girlfriend is, what her age is, and then calculate her age raised to the 0.43 power. To do this, I will use the web_search tool to find the answer to who Leo DiCaprio's girlfriend is, then I will use the web_search tool again to find out what her age is.  After I have Leo DiCaprio's girlfriend's age, I will use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power.  The required arguments for the web_search tool is the query.  The required arguments for the calculate_power tool is the number and the power. 

The steps I need to follow are:
Step 1: Use the web_search tool to find the answer to who Leo DiCaprio's girlfriend is. (The required arguments are 'query')
Step 2: Use the web_search tool to find out what her age is. (The required arguments are 'query')
Step 3: Use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power. (The required arguments are 'number', and 'power')
Step 4: Return the final answer of what Leo DiCaprio's girlfriend's age raised to the 0.43 power is to the user.

web_search Tool Query: Who is Leo DiCaprio's girlfriend?

Action:
```json
{{
  "action": "web_search",
  "action_input": {{
    "query": "Who is Leo DiCaprio's girlfriend?"
  }}
}}
```
Observation: 
Leo DiCaprio's girlfriend is Vittoria Ceretti.

Original User Input: Who is Leo DiCaprio's girlfriend? What is her current age raised to the 0.43 power?

Thought: Did any of the previous steps give me enough data to answer the question? No, I am only on Step 1, I still need to find Vittoria Ceretti's age. I will use the web_search tool again to find out what her age is.  After I have Leo DiCaprio's girlfriend's age, I will use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power.  The required arguments for the web_search tool is the query.  The required arguments for the calculate_power tool is the number and the power. 

The steps I need to follow are:
Step 1: COMPLETE
Step 2: Use the web_search tool to find out what her age is. (The required arguments are 'query')
Step 3: Use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power. (The required arguments are 'number', and 'power')
Step 4: Return the final answer of what Leo DiCaprio's girlfriend's age raised to the 0.43 power is to the user.

web_search Tool Query: What is Vittoria Ceretti's age?

Action:
```json
{{
  "action": "web_search",
  "action_input": {{
    "query": "What is Vittoria Ceretti's age?"
  }}
}}
```
Observation: 
Vittoria Ceretti is 25.

Original User Input: Who is Leo DiCaprio's girlfriend? What is her current age raised to the 0.43 power?

Thought: Did any of the previous steps give me enough data to answer the question? No, I am only on Step 2, I still need to calculate Vittoria Ceretti's age raised to the 0.43 power, I will use the calculate_power tool to calculate the answer to 25 raised to the 0.43 power.  The required arguments for the calculate_power tool is the number and the power. 

The steps I need to follow are:
Step 1: COMPLETE
Step 2: COMPLETE
Step 3: Use the calculate_power tool to calculate the answer to her current age raised to the 0.43 power. (The required arguments are 'number', and 'power')
Step 4: Return the final answer of what Leo DiCaprio's girlfriend's age raised to the 0.43 power is to the user.

calculate_power Tool Query: number=25, power=0.43

Action:
```json
{{
  "action": "calculate_power",
  "action_input": {{
    "number": 25,
    "power": 0.43
  }}
}}
```
Observation: 
3.991298452658078

Original User Input: Who is Leo DiCaprio's girlfriend? What is her current age raised to the 0.43 power?

Thought: Did any of the previous steps give me enough data to answer the question? Yes, I have used the web_search and calculate_power tools to arrive at the final answer to the original query, which is 3.991298452658078. I will return the final answer to the user.

The steps I need to follow are:
Step 1: COMPLETE
Step 2: COMPLETE
Step 3: COMPLETE
Step 4: Return the final answer of what Leo DiCaprio's girlfriend's age raised to the 0.43 power is to the user.

Action:
```json
{{
  "action": "Final Answer",
  "action_input": "Leo DiCaprio's girlfriend is Vittoria Ceretti, who is 25 years old. Her age raised to the 0.43 power is 3.991298452658078."
}}
```
--- END MULTI-HOP EXAMPLE ---

Additional user information:
{system_information}

Review the previous instructions carefully. Remember to ALWAYS respond with a SINGLE valid json blob of a SINGLE action (you will get a chance to perform more actions later), following the Thought/Steps/Action/Observation pattern in the examples above. Use the tools available to you if necessary, and make sure you've created a JSON blob that satisfies ALL of the required fields to use any tools you select.

If you don't require a tool to complete the rest of the steps, please complete them and respond with a final answer.

You are iterating over (possibly) multiple calls to tools. Please take into account the user query below, and then your previous work (if any). If you have previously used a tool, the output will be here.
"""


PLAN_STEPS_TEMPLATE = """{system_prompt}

You have access the following tools that you can use by returning the appropriately formatted JSON. Don't make up tools, only ever use the tools that are listed here. If a query does not require the use of a tool (such as when you know the answer, or the answer exists in this context), you can return an answer to the user instead.  If there are no tools available, or if none of the available tools suit your purpose, you should answer the user instead of using a tool.
--- AVAILABLE TOOLS ---
{available_tools}
--- AVAILABLE TOOLS ---
Pay close attention to the required arguments for each tool, and make sure to include them in the JSON output if you are using a tool.

The loaded documents that you have access to are below.
--- LOADED DOCUMENTS ---
{loaded_documents}
--- LOADED DOCUMENTS ---

Any previous conversation with the user is contained here. The chat history may contain context that you find useful to answer the current query.
--- CHAT HISTORY ---
{chat_history}
--- CHAT HISTORY ---

--- USER QUERY ---
{user_query}
--- USER QUERY ---

Read the user's query very carefully. I need you to help me to plan the appropriate actions to take in order to answer the user's query.

Please break the user's query down into stand-alone steps that use the available tools in order to answer the user's query.  Make sure that each step contains enough information to be acted upon on it's own.

All responses are JSON blobs with the following format:
```json
{{
  "steps": [
    {{"step_num": <<step number>>, "step_description": "<<describe the step in detail here>>", "tool": "<<tool name (one of the available tools)>>", "relies_on": [<<list other step IDs this step relies on, if any>>], "tool_args": {{"arg name": "arg value", "another arg name": "another arg value"}}}},
    ...
  ]
}}

When providing the tool_args, if the tool arguments require the output of a previous step- please use the specific placeholder: "PLACEHOLDER_VALUE" (without the quotes).  For example, if the user's query is "What's the weather like here?", you might split this into two steps- getting the user's location, and then getting the weather for that location.  Assuming the get_location tool takes no arguments, your response would look like this:
```json
{{
  "steps": [
    {{"step_num": 1, "step_description": "Get the user's current location", "tool": "get_location", "relies_on": []}},
    {{"step_num": 2, "step_description": "Get the weather for the user's location", "tool": "get_weather", "relies_on": [1,], "tool_args": {{"location": "PLACEHOLDER_VALUE"}}}}
  ]
}}
```

Please take note of the "relies_on" field in the JSON output.  This field is used to indicate which previous steps this step relies on.  If a step does not rely on any previous steps, this field should be an empty list.  If a step relies on a previous step, the "relies_on" field should contain a list of the step numbers that this step relies on.  For example, if step 3 relies on steps 1 and 2, the "relies_on" field for step 3 should be [1, 2].

If you already know the answer to the user's query, or do not have the appropriate tools to create any steps with (remember not to make up tools), you should respond with the following JSON blob:
```json
{{
  "final_answer": "<<your complete answer here>>"
}}
```
Only reply with a final answer if you can completely answer the user's query.

AI: Sure! Here is my response (in JSON format) that are all using the various tools you provided (I am definitely not making up tools!) to me (or answering directly), and that can be used to answer the user's query:
"""
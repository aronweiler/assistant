from langchain.prompts import PromptTemplate

MULTI_PROMPT_ROUTER_TEMPLATE = """\
<< SYSTEM INFORMATION >>
{{system_information}}

Given a raw text input to a language model, select the model best suited for processing \
the input. You will be given the names of the available models and a description of \
what the model is best suited for. 

Use the provided chat history to help rephrase the input so that it is a stand-alone question \
by doing things like resolving coreferences in the input (e.g. assigning names to things like "him", or places like "here", or dates like "tomorrow", etc).

<< CHAT HISTORY >>
{{chat_history}}

<< FORMATTING >>
Return a markdown code snippet with a JSON object formatted to look like:
```json
{{{{
    "destination": string \\ name of the prompt to use or "DEFAULT"
    "next_inputs": string \\ a potentially modified version of the original input
}}}}
```

REMEMBER: "destination" MUST be one of the candidate prompt names specified below OR \
it can be "DEFAULT" if the input is not well suited for any of the candidate prompts.
REMEMBER: "next_inputs" can just be the original input if you don't think any \
modifications are needed.

<< CANDIDATE MODELS >>
{destinations}

<< INPUT >>
{{input}}

<< OUTPUT >>
"""

#AGENT_TEMPLATE = "{system_information}\n{user_name} ({user_email}): {input}\n\n{agent_scratchpad}"
AGENT_TEMPLATE = "{user_name} ({user_email}): {input}\n\n{agent_scratchpad}"

TOOLS_SUFFIX = """Use any context you may need from the history:
---  TOOL HISTORY ---
{agent_chat_history}
--- TOOL HISTORY ---

Helpful system information: {system_information}

Let's think this through, and be very careful to use the right tool arguments in the json blob.

Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary. Respond directly if appropriate. Format is Action:```$JSON_BLOB```, then Observation:.
Thought:"""

CONVERSATIONAL_TEMPLATE = """{system_prompt}
System information:
{system_information}
Possibly related context:
{context}
Current conversation:
{chat_history}
{user_name} ({user_email}): {input}
AI:"""
        
CONVERSATIONAL_PROMPT = PromptTemplate(
    input_variables=[
        "system_prompt",
        "system_information",
        "context",
        "user_name",
        "user_email",
        "chat_history",
        "input",
    ],
    template=CONVERSATIONAL_TEMPLATE
)

MEMORY_TEMPLATE = """Below is a query from a user.  I have included some context that may be helpful.

Please read the query carefully, and then try to answer the query using the context provided.

------- BEGIN CONTEXT -------
{context}
------- END CONTEXT -------

QUERY:
{input}

If the context does not answer the query, respond with "I don't know".

Answer:
"""

MEMORY_PROMPT = PromptTemplate(
    input_variables=[
        "context",
        "input"
    ],
    template=MEMORY_TEMPLATE
)

SUMMARIZE_FOR_LABEL_TEMPLATE = """
Summarize the following statement in a few words (no more than 5), with the intent of making a label for an interaction.

Examples: 
"Tell me how to do long division, step by step please." -> "How to do long division"
"Can you tell me how to make a cake?" -> "How to make a cake"
"What time is it?" -> "What time is it"
"Who is the president of the United States?" -> "President of the United States"
"Where is the nearest grocery store?  Do they sell cake?" -> "Nearest grocery store"

Do not include punctuation in your summary, such as question marks, periods, or exclamation points.
Do not include any words that are not necessary to understand the statement.
Do not include any kind of preamble, such as "the summary is..." or anything of the sort.

--- BEGIN Statement to Summarize ---
{query}
--- END Statement to Summarize ---

ONLY return the very short summary, nothing else.

Sure, here you go:
"""

SECONDARY_AGENT_ROUTER_TEMPLATE = """System information:
{system_information}

You are an AI checking another AI's work.  Your job is to evaluate the following query from a User and a response from another AI that is answering the query.

--- BEGIN USER QUERY (with chat history) ---
{chat_history}
--- END USER QUERY ---

--- BEGIN AI RESPONSE ---
{response}
--- END AI RESPONSE ---

Review the query and the response above. 

If the AI RESPONSE contains the answer to the user's query, respond only with "YES".

If the AI RESPONSE does not answer the user's query, or there are factual errors with the response, rephrase the question from the USER QUERY into a stand-alone question, and respond only with that.

AI: """

DOCUMENT_TEMPLATE = """{system_prompt}
System information:
{system_information}
Related context:
{context}
Current conversation:
{chat_history}
{user_name} ({user_email}): {query}
AI:"""
        
DOCUMENT_PROMPT = PromptTemplate(
    input_variables=[
        "system_prompt",
        "system_information",
        "context",
        "user_name",
        "user_email",
        "chat_history",
        "query",
    ],
    template=DOCUMENT_TEMPLATE
)
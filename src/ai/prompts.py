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
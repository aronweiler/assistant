from langchain.prompts import PromptTemplate

MULTI_PROMPT_ROUTER_TEMPLATE = """\
Given a raw text input to a language model select the model prompt best suited for \
the input. You will be given the names of the available prompts and a description of \
what the prompt is best suited for. You may also revise the original input if you \
think that revising it will ultimately lead to a better response from the language \
model.  Use the provided chat history to help rephrase the input so that it is a stand-alone question. \
(by doing things like resolving coreferences in the input, etc.)

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

<< CANDIDATE PROMPTS >>
{destinations}

<< INPUT >>
{{input}}

<< OUTPUT >>
"""

CONVERSATIONAL_TEMPLATE = """{system_prompt}
System information:
{system_information}
Current conversation:
{chat_history}
{user_name} ({user_email}): {input}
AI:"""
        
CONVERSATIONAL_PROMPT = PromptTemplate(
    input_variables=[
        "system_prompt",
        "system_information",
        "user_name",
        "user_email",
        "chat_history",
        "input",
    ],
    template=CONVERSATIONAL_TEMPLATE
)

TOOLS_TEMPLATE = """System information:
{system_information}
Location: {location}
{user_name} ({user_email}): {input}
"""

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

INTERNET_SEARCH_TEMPLATE = """Use one of the tools available to you to answer the following query.

QUERY:
{input}

Answer:
"""

INTERNET_SEARCH_PROMPT = PromptTemplate(
    input_variables=[
        "input"
    ],
    template=INTERNET_SEARCH_TEMPLATE
)
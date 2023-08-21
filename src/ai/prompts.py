from langchain.prompts import PromptTemplate

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
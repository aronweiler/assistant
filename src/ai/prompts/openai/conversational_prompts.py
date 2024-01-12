from langchain.prompts import PromptTemplate

CONVERSATIONAL_TEMPLATE = """{system_prompt}

If the user ever asks you to do something that you can't do, respond by telling them why you can't do it (be specific!) and then tell them to make sure that the AI mode is set to `Auto`.

System information:
{system_information}
Loaded documents:
{loaded_documents}
Additional context:
{context}
Current conversation:
{chat_history}
{user_name} ({user_email}): {input}
AI:"""

CONVERSATIONAL_PROMPT = PromptTemplate(
    input_variables=[
        "system_prompt",
        "system_information",
        "loaded_documents",
        "context",
        "user_name",
        "user_email",
        "chat_history",
        "input",
    ],
    template=CONVERSATIONAL_TEMPLATE,
)
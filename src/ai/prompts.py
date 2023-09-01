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

<< LOADED DOCUMENTS >>
{{loaded_documents}}

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

# Use any context you may need from the history:
# ---  TOOL HISTORY ---
# {agent_chat_history}
# --- TOOL HISTORY ---

TOOLS_SUFFIX = """Helpful system information: {system_information}

Let's think this through, and be very careful to use the right tool arguments in the json blob.

--- FORMAT --- 
Action:
```$JSON_BLOB```
--- FORMAT --- 

Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary. Respond directly if appropriate. 

"""

CONVERSATIONAL_TEMPLATE = """{system_prompt}
System information:
{system_information}
Loaded documents:
{loaded_documents}
Possibly related conversation context:
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

REPHRASE_TO_KEYWORDS_TEMPLATE = """Your job is to rephrase the following user input into a stand-alone set of keywords to use when searching a document.  This means that the rephrased input should be able to be understood without any other context besides the input itself (resolve coreferences such as he/him/her/she/it/they, etc.).  Use any of the available chat history, system information, or documents to help you rephrase the user's input into a stand-alone set of keywords.

System information:
{system_information}

Chat history:
{chat_history}

Documents available:
{loaded_documents}

------- BEGIN USER INPUT TO REPHRASE -------
{user_name} ({user_email}): {input}
------- END USER INPUT TO REPHRASE -------

AI: I have rephrased the user input as search keywords so that it can be understood without any other context:
"""

REPHRASE_TEMPLATE = """Your job is to rephrase the following user input into a stand-alone question or statement.  This means that your rephrased question or statement should be able to be understood without any other context besides the question or statement itself.  Use any of the available chat history, system information, or documents to help you rephrase the user's input into a stand-alone question or statement.  Do not otherwise modify the user's input.

System information:
{system_information}

Chat history:
{chat_history}

Documents available:
{loaded_documents}

------- BEGIN USER INPUT TO REPHRASE -------
{user_name} ({user_email}): {input}
------- END USER INPUT TO REPHRASE -------

AI: I have rephrased the user input so that it can be understood without any other context:
"""
        
REPHRASE_PROMPT = PromptTemplate(
    input_variables=[
        "system_information",
        "user_name",
        "user_email",
        "chat_history",
        "loaded_documents",
        "input",
    ],
    template=REPHRASE_TEMPLATE
)

SINGLE_LINE_SUMMARIZE_TEMPLATE = """Provide a single-line summary of the following text, making sure to capture important details, such as thematically important people, organizations, places, etc.  This summary will be used to help route requests to the appropriate AI, based on the content of the text- so while your summary should be very short, it should also be as detailed as possible.

{text}

SINGLE LINE SUMMARY:
"""

SINGLE_LINE_SUMMARIZE_PROMPT = PromptTemplate.from_template(SINGLE_LINE_SUMMARIZE_TEMPLATE)

CONCISE_SUMMARIZE_TEMPLATE = """Write a concise summary of the following:

{text}

CONCISE SUMMARY:
"""

SIMPLE_SUMMARIZE_PROMPT = PromptTemplate.from_template(CONCISE_SUMMARIZE_TEMPLATE)

SIMPLE_REFINE_TEMPLATE = """Your job is to produce a final summary of the following text. We have provided an existing summary up to a certain point: 

----- BEGIN EXISTING SUMMARY -----
{existing_answer}
----- BEGIN EXISTING SUMMARY -----

Now you have the opportunity to refine the existing summary (only if needed) with some more context below.

----- BEGIN ADDITIONAL CONTEXT -----
{text}
----- END ADDITIONAL CONTEXT -----

Given the new context, refine the original summary.  If the context isn't useful, just return the original summary.
"""

SIMPLE_REFINE_PROMPT = PromptTemplate.from_template(SIMPLE_REFINE_TEMPLATE)
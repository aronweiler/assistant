from langchain.prompts import PromptTemplate

MULTI_PROMPT_ROUTER_TEMPLATE = """<< SYSTEM INFORMATION >>
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
    "destination": string \\ name of the MODEL to use. Must be one of the candidate model specified below.
    "next_inputs": string \\ a potentially modified version of the original input
}}}}
```

REMEMBER: "destination" MUST be one of the candidate model names specified below.
REMEMBER: "next_inputs" can just be the original input if you don't think any modifications are needed.

<< CANDIDATE MODELS >>
{destinations}

<< INPUT >>
{{input}}

<< OUTPUT >>
"""

#AGENT_TEMPLATE = "{system_information}\n{user_name} ({user_email}): {input}\n\n{agent_scratchpad}"
AGENT_TEMPLATE = "{user_name} ({user_email}): {input}\n\n{agent_scratchpad}"

TOOLS_FORMAT_INSTRUCTIONS = """Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).

Valid "action" values: "Final Answer" or {tool_names}

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

Query: <<user input query>>

Thought: <<Describe your thinking on the previously taken steps and plan subsequent steps.  If the data exists to answer the users query, return the final answer.>>

Action:
```
$JSON_BLOB
```

Observation: <<action result>>

... (repeat Thought/Action/Observation as many times as necessary to get to the final answer)

When you arrive at the final answer to the query, the format is:
```json
{{{{
  "action": "Final Answer",
  "action_input": "<<Your final response to the user>>"
}}}}
```"""

TOOLS_SUFFIX = """Use any context you may need from the chat history (e.g. document names, or other information):
---  CHAT HISTORY ---
{agent_chat_history}
--- CHAT HISTORY ---

Helpful system information: {system_information}

Let's think this through, and be very careful to use the right tool arguments in the json blob.

--- FORMAT --- 
Action:
```json
$JSON_BLOB
```
--- FORMAT --- 

Begin! Reminder to ALWAYS respond with a valid json blob of a single action, following the Thought/Action/Observation pattern. Use tools if necessary. Respond directly if appropriate. DO NOT respond with the same action twice in a row!  Each action you take should be different from the previous action.

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

REPHRASE_TEMPLATE = """Your job is to rephrase the following user input into a stand-alone question or statement.  This means that your rephrased question or statement should be able to be understood without any other context besides the question or statement itself.  

Use the available chat history, system information, and files to help you rephrase the user's input into a stand-alone question or statement.  Do not otherwise modify the user's input.

Be sure to resolve all coreferences in the input (e.g. assign names to things like "that", "this", "her", "him", or places like "here", or dates like "tomorrow", etc).  If the coreference refers to a file, be sure to include the full name and ID of the file in your rephrased question or statement.

For example, if the user says "Tell me about that file", you should determine what "that file" is referring to (by looking at the available files), and then rephrase the question as "Tell me about '<<that file>>'" (replacing <<that file>> with the actual file name and ID from the list of available files).  If the user asks you to "elaborate on that", they are likely referring to something in the chat history, so you should rephrase the question as "Elaborate on '<<the entity>>'" (replacing <<the entity>> with the actual entity from the chat history).

System information:
{system_information}

Chat history (use this to resolve coreferences):
{chat_history}

------- BEGIN USER INPUT TO REPHRASE -------
{user_name} ({user_email}): {input}
------- END USER INPUT TO REPHRASE -------

-- AVAILABLE FILE IDs --
{loaded_documents}

When referencing any of the available files, you MUST include the ID of the file when referencing that file in your output.  For example, if a user references a file named "my_file.txt", you should rephrase the user's input as "Tell me about 'my_file.txt' (file_id: 12345)".

AI: I have rephrased the user input so that it can be understood without any other context by resolving any ambiguous references and coreferences, ensuring that any files are referred to by their full name AND file_id:
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

SIMPLE_REFINE_TEMPLATE = """Your job is to produce a final summary of the following text with the goal of answering a user's query. Below is provided an existing summary up to a certain point: 

----- BEGIN EXISTING SUMMARY -----
{existing_answer}
----- BEGIN EXISTING SUMMARY -----

Now you have the opportunity to refine the existing summary (only if needed) with some more context below.

----- BEGIN ADDITIONAL CONTEXT -----
{text}
----- END ADDITIONAL CONTEXT -----

----- BEGIN USER QUERY -----
{query}
----- END USER QUERY -----

Given the new context, refine the original summary with the goal of answering the user's query.  If the context isn't useful, just return the original summary.
"""

SIMPLE_REFINE_PROMPT = PromptTemplate.from_template(SIMPLE_REFINE_TEMPLATE)

QUESTION_PROMPT_TEMPLATE = """Use the following portion(s) of a long document to see if any of the text is relevant to answer the question. 
Return any relevant text verbatim, including citations, if any.

--- BEGIN EXAMPLE ---
CONTENT: 
ARON WEILER
aronweiler@gmail.com · www.linkedin.com/in/aronweiler ·
SUMMARY
With over 20 years of experience in the software industry, I bring to the table a
broad range of project management and product development skills- from customer
interactions for user needs gathering and analysis, to requirements, specifications,
architecture, design, planning, and implementation.
SOURCE: file_id='1234', file_name='aron weiler resume.pdf', page='1'

CONTENT: 
SEPT 2002 – JUL 2004
SENIOR SOFTWARE ENGINEER
OFFICETOOL.COM, INC.
Hired in September of 2002, I was brought aboard as a contractor for my skills in
Microsoft’s .NET programming languages. After that, I was hired on as a full-time
employee, managed several projects with multiple programmers, developed
applications from beginning to end independently, participated in training other
developers on the .NET architecture as well as testing and maintaining new and
existing applications.
SOURCE: file_id='1234', file_name='aron weiler resume.pdf', page='5'

Question: describe the job Aron had in 2004

Relevant text, if any, including document and page citations (in Markdown format):
Aron Weiler held the position of Senior Software Engineer at **OFFICETOOL.COM, INC.** from Sept 2002 to Jul 2004.

Here are some details about the position:

- Joined in September 2002 as a contractor, leveraging expertise in Microsoft's .NET programming languages.
- Transitioned to a full-time employee role.
- Managed multiple projects with cross-functional teams of programmers.
- Independently developed applications from inception to completion.
- Conducted training sessions for fellow developers on the .NET architecture.
- Assisted in testing and maintenance of both new and existing applications.

*Source: [aron weiler resume.pdf (Page 5)](/files?file_id=1234&page=5)*
--- END EXAMPLE ---

{summaries}

Question: {question}

Relevant text, if any, including document and page citations (in Markdown format):
"""

QUESTION_PROMPT = PromptTemplate(
    template=QUESTION_PROMPT_TEMPLATE, input_variables=["summaries", "question"]
)

COMBINE_PROMPT_TEMPLATE = """Given the following extracted parts of a long document and a question, create a final answer with references ("SOURCES"). 
If you don't know the answer, just say that you don't know. Don't try to make up an answer.
ALWAYS return a "SOURCES" part in your answer.

Every response should follow this format:
--- BEGIN EXAMPLE RESPONSE --- 
FINAL ANSWER: << your answer here >>
SOURCES: << sources here >>
--- END EXAMPLE RESPONSE --- 

QUESTION: {question}

Extracted Document Parts:
=========
{summaries}
=========

FINAL ANSWER:"""
COMBINE_PROMPT = PromptTemplate(
    template=COMBINE_PROMPT_TEMPLATE, input_variables=["summaries", "question"]
)

DOCUMENT_PROMPT_TEMPLATE = """CONTENT: \n{page_content}\nSOURCE: file_id='{file_id}', file_name='{filename}', page='{page}'"""

DOCUMENT_PROMPT = PromptTemplate(
    template=DOCUMENT_PROMPT_TEMPLATE, input_variables=["page_content", "page", "filename", "file_id"]
)
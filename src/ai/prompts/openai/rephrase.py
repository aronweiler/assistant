from langchain.prompts import PromptTemplate

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
    template=REPHRASE_TEMPLATE,
)
from langchain.prompts import PromptTemplate

CODE_PROMPT_TEMPLATE = """CONTENT: \n{page_content}\nSOURCE: file_id='{file_id}', file_name='{filename}, line={start_line}'"""

CODE_PROMPT = PromptTemplate(
    template=CODE_PROMPT_TEMPLATE,
    input_variables=["page_content", "filename", "file_id", "start_line"],
)

CODE_DETAILS_EXTRACTION_TEMPLATE = """Please examine the following code carefully:

----- CODE -----
{code}
----- CODE -----

I would like you to extract a list of keywords that can be used to later search this code. The keywords should include things like variable names, function names, class names, and other items of interest. Please also include short descriptions (no more than a sentence or two) of the goals and functionality that is represented in this code, being sure to capture any functionality that could be of interest to someone searching the codebase.

At the very least, there should be a short description of each function within the code (e.g. 'get_chat_history: Retrieves the chat history from the conversation manager.'), but you should also include descriptions of any other interesting functionality that is represented in the code.

Additionally, please write a detailed summary of what this code does. This summary should be at least a paragraph long, and should be written in a way that is understandable to someone who is not familiar with the codebase.

Your output should be in a JSON blob with the following format:

```json
{{
    "keywords": [
        "list",
        "of",
        "keywords"
    ],
    "descriptions": [
        "short description 1",
        "short description 2",
        "etc."        
    ],
    "summary": "detailed summary"
}}
```

Please make sure that the JSON is valid and properly formatted.

AI: Sure, here is a JSON blob with the keywords, descriptions, and summary:
"""

IDENTIFY_LIKELY_FILES_TEMPLATE = """Please take a look at the following code file summaries and identify which ones are most likely to contain the code that is relevant to the user's query. You can select multiple summaries if you think that multiple files are likely to contain the code that you are looking for.

User Query: {user_query}

{summaries}

Please read the details of the files above, and respond with a list of the file IDs most likely to match the user's query in the following JSON format. For example, if you think that the files with IDs 23, and 44 are likely to contain the relevant code, you would respond with the following:

```json
[23, 44, ...]
```

As a reminder, you're looking for code that answers the user's query of: {user_query}

AI: Sure, here are the file IDs (in JSON list form) that are most likely to contain the relevant code:
"""

ANSWER_QUERY_TEMPLATE = """I would like you to examine the following code very carefully, and answer the user's query of: {user_query}

{code_contents}

Remember, the user's query is: {user_query}

Please provide an answer if possible.  If the code does not contain an answer to the user's query, please respond with an explanation of why the code does not contain an answer.

If the code above can be used to answer the query, be sure to include the file names of the code that contained the answer.

AI: Sure, I have examined the code, and here is my response:
"""

GET_RELEVANT_SNIPPETS_TEMPLATE = """Please examine the following code carefully:

file_id: {file_id}
file_name: {file_name}
```
{code}
```

I would like you to extract a list of relevant code snippets from the code above that relates to the description below.

Description: {description}

Please provide a list of code snippets in a JSON blob with the following format:

```json
[
    {{
        "file_id": 123,
        "start_line": 12,
        "end_line": 15,
        "code": "code snippet"
    }},
    {{
        "file_id": 456,
        "start_line": 1,
        "end_line": 5,
        "code": "code snippet"
    }},
    ...
]
```

If none of the provided code is relevant to the description, please respond with an empty list. (e.g. `[]`)  If responding with an empty list, do not respond with any other text at all (such as an explanation)- just the empty list.

AI: Sure, here is a JSON blob with the relevant code snippets:
"""
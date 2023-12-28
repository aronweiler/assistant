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

AI: Sure, here is a JSON blob with the keywords, descriptions, and summary:
"""

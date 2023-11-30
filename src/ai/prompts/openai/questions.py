CHUNK_QUESTIONS_TEMPLATE = """Given the following chunk of a larger document, please come up with {number_of_questions} unique questions that could be answered using this context. 

--- CONTEXT ---
{document_text}
--- CONTEXT ---

Please format your response as a Markdown formatted JSON list with the following structure:    
```json
["question 1", "question 2", "etc.", ...]
```

Think carefully and try to align your questions with the kind of questions a user may ask about the content of this text.  Additionally, try to make each question unique, and not a duplicate of another question.  For example, if the context is about the weather, don't ask "What is the temperature?" and "What is the temperature in degrees?" as these are essentially the same question.  Instead, ask "What is the temperature?" and "What is the humidity?".

Remember to only ever return a JSON list of questions, and nothing else.

AI: Sure thing! Here are {number_of_questions} questions that could be answered using this context (in JSON list format):
"""
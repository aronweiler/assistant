CHUNK_QUESTIONS_TEMPLATE = """Given the following chunk of text, please come up with {number_of_questions} unique questions that could be answered using this context. 

--- CONTEXT ---
{document_text}
--- CONTEXT ---

Think carefully and try to align your questions with the kind of questions a user may ask about the content of this text.  It's important to try to cover the breadth of the content, and not just focus on one aspect.  Your goal should be to make the questions as varied as possible.

Additionally, try to make each question unique, and not a duplicate of another question.  For example, if the context is about the weather, don't ask "What is the temperature?" and "What is the temperature in degrees?" as these are essentially the same question.  Instead, ask "What is the temperature?" and "What is the humidity?"."""
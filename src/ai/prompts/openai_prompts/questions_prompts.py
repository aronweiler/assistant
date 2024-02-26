CHUNK_QUESTIONS_TEMPLATE = """Please do two things for me:

1. Create a summary of the provided document chunk.
2. Generate {number_of_questions} unique questions that could be answered using this document chunk.

----- BEGIN DOCUMENT CHUNK -----
{document_text}
----- END DOCUMENT CHUNK -----

# Summary Instructions:
The summary should capture all key points and relevant details to provide a solid foundation for understanding the document's content. The summary will be used by another AI or user to grasp the essence of this section without reading it in full.

Please adhere to these guidelines when creating the summary:
- Identify and highlight the main ideas, arguments, or events presented in the text.
- Include any important data, statistics, names, dates, or locations that are crucial for understanding the context.
- Maintain neutrality and objectivity, avoiding personal opinions or interpretations.
- Ensure that your summary is coherent and flows logically from start to finish.
- Use bullet points or numbered lists where appropriate to organize information clearly.


After reviewing the text:
- Provide a concise yet comprehensive overview that encapsulates all significant aspects of the document chunk.
- If certain information is implied but not explicitly stated in the text, you may include such inferences, clearly marking them as interpretations.
- Avoid including extraneous details that do not contribute to a fundamental understanding of the text.

Remember not to fabricate any information. If you do not know something or if certain information is missing from the chunk provided, simply state that specific details are not available within this section.

# Question Generation Instructions:
Please generate {number_of_questions} unique questions that could be answered using this document chunk. Think carefully and try to align your questions with the kind of questions a user may ask about the content of this text. It's important to try to cover the breadth of the content, and not just focus on one aspect. Your goal should be to make the questions as varied as possible.

Additionally, try to make each question unique, and not a duplicate of another question.  For example, if the document chunk contains details about the weather, don't generate questions such as "What is the temperature?" and "What is the temperature in degrees?", since these are essentially the same question.  Instead, generate something that approaches the text from a different angle, such as "What is the temperature?" and "What is the humidity?"."""
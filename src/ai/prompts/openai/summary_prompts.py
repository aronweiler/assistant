from langchain.prompts import PromptTemplate

SUMMARIZE_FOR_LABEL_TEMPLATE = """
Summarize the following statement in a few words (no more than 5), with the intent of making a label for an conversation.

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

Your response should be in JSON, with the following format:
{{
    "answer": "The text of your response goes here."
}}

AI: Sure, here you go:
"""

DETAILED_SUMMARIZE_TEMPLATE = """Write a detailed summary of the following:

{text}

DETAILED SUMMARY:
"""

DETAILED_SUMMARIZE_PROMPT = PromptTemplate.from_template(DETAILED_SUMMARIZE_TEMPLATE)

SIMPLE_REFINE_TEMPLATE = """Your job is to produce a final summary of the following text so that another AI can use your summary to answer the user's query. Below is provided an existing summary up to a certain point: 

----- BEGIN EXISTING SUMMARY -----
{existing_answer}
----- END EXISTING SUMMARY -----

Now you have the opportunity to refine or enhance the existing summary (only if needed) with some more context below.

Please consider these guidelines when refining the summary:
- If the additional context directly addresses the user's query, integrate this information succinctly into the existing summary.
- If there are discrepancies between the existing summary and additional context, resolve them for accuracy.
- Maintain neutrality and objectivity in the summary, avoiding any personal opinions or interpretations.
- Ensure that the final summary is coherent and flows logically from start to finish.
- Use bullet points or numbered lists where appropriate to enhance readability and organization.

----- BEGIN ADDITIONAL CONTEXT -----
{text}
----- END ADDITIONAL CONTEXT -----

----- BEGIN USER QUERY -----
{query}
----- END USER QUERY -----

After reviewing both the existing summary and additional context:
- If the additional context contains information relevant to the user's query, use it to add essential details or clarify points in the existing summary.
- If the additional context isn't useful, or is unrelated to the user's query, confirm that the existing summary sufficiently answers the query and return it without changes.
- In cases where neither the existing summary nor additional context address the user's query, please indicate that no relevant information is available.

By adhering to these guidelines, you will help ensure that the final summary is not only informative and relevant but also clear and professional in its presentation.

Remember not to fabricate any information. If you do not know something or if certain information is missing, simply state that you don't know or that information is not provided.

If the additional context is not useful, or is unrelated to the user's query, return the existing summary without changes.

AI: 
"""

SIMPLE_REFINE_PROMPT = PromptTemplate.from_template(SIMPLE_REFINE_TEMPLATE)


DETAILED_DOCUMENT_CHUNK_SUMMARY_TEMPLATE = """Your job is to write a detailed summary of the following piece of a larger document. This summary should capture all key points and relevant details to provide a solid foundation for understanding the document's content. The summary will be used by another AI or user to grasp the essence of this section without reading it in full.

Please adhere to these guidelines when creating the summary:
- Identify and highlight the main ideas, arguments, or events presented in the text.
- Include any important data, statistics, names, dates, or locations that are crucial for understanding the context.
- Maintain neutrality and objectivity, avoiding personal opinions or interpretations.
- Ensure that your summary is coherent and flows logically from start to finish.
- Use bullet points or numbered lists where appropriate to organize information clearly.

----- BEGIN DOCUMENT CHUNK -----
{text}
----- END DOCUMENT CHUNK -----

DETAILED SUMMARY:

After reviewing the text:
- Provide a concise yet comprehensive overview that encapsulates all significant aspects of the document chunk.
- If certain information is implied but not explicitly stated in the text, you may include such inferences, clearly marking them as interpretations.
- Avoid including extraneous details that do not contribute to a fundamental understanding of the text.

Remember not to fabricate any information. If you do not know something or if certain information is missing from the chunk provided, simply state that specific details are not available within this section.

By adhering to these guidelines, you will help ensure that the initial summary is informative, accurate, and useful for anyone who needs to understand this part of the document without reading it in full.

AI:
"""

SIMPLE_DOCUMENT_REFINE_TEMPLATE = """Your job is to produce a final summary of an entire document that has been split into chunks. You will be provided a summary of all prior chunks, and one additional chunk.
Use the additional chunk to add to the summary. Do not remove information from the summary unless it is contradicted by information in the current chunk.
The summary in progress is provided below:

----- BEGIN EXISTING SUMMARY -----
{existing_answer}
----- END EXISTING SUMMARY -----

Below is an additional chunk that you should consider for an addition to the ongoing summary:

----- BEGIN ADDITIONAL CHUNK -----
{text}
----- END ADDITIONAL CHUNK -----

Given the additional chunk, refine the original summary by adding to or modifying the existing summary. If the additional chunk isn't useful for adding to the summary, just return the existing summary.
"""

SIMPLE_DOCUMENT_REFINE_PROMPT = PromptTemplate.from_template(
    SIMPLE_DOCUMENT_REFINE_TEMPLATE
)

REDUCE_SUMMARIES_TEMPLATE = """The following is set of summaries generated from a number of document chunks:

{doc_summaries}

Please take these summaries, and distill it into a final (detailed) consolidated summary.
"""

REDUCE_SUMMARIES_PROMPT = PromptTemplate(
    template=REDUCE_SUMMARIES_TEMPLATE, input_variables=["doc_summaries"]
)
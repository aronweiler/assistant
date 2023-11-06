from langchain.prompts import PromptTemplate

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

AI: Sure, here you go:
"""

DETAILED_SUMMARIZE_TEMPLATE = """Write a detailed summary of the following:

{text}

DETAILED SUMMARY:
"""

DETAILED_SUMMARIZE_PROMPT = PromptTemplate.from_template(DETAILED_SUMMARIZE_TEMPLATE)

SIMPLE_REFINE_TEMPLATE = """Your job is to produce a final summary of the following text with the goal of answering a user's query. Below is provided an existing summary up to a certain point: 

----- BEGIN EXISTING SUMMARY -----
{existing_answer}
----- END EXISTING SUMMARY -----

Now you have the opportunity to refine or enhance the existing summary (only if needed) with some more context below.

----- BEGIN ADDITIONAL CONTEXT -----
{text}
----- END ADDITIONAL CONTEXT -----

----- BEGIN USER QUERY -----
{query}
----- END USER QUERY -----

If the additional context contains information relevant to the user's query, use it to add additional information to the summary.  If the additional context isn't useful, or is unrelated to the user's query, just return the existing summary.
"""

SIMPLE_REFINE_PROMPT = PromptTemplate.from_template(SIMPLE_REFINE_TEMPLATE)


DETAILED_DOCUMENT_CHUNK_SUMMARY_TEMPLATE = """Write a detailed summary of the following piece of a larger document:

{text}

DETAILED SUMMARY:
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
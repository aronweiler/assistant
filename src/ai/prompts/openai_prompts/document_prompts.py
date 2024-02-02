from langchain.prompts import PromptTemplate

QUESTION_PROMPT_TEMPLATE = """Use the following portion(s) of a long document to see if any of the text is relevant to answer the question. 
Return any relevant text verbatim, including citations of page or line numbers, if any.

{summaries}

Question: {question}"""

DOCUMENT_PROMPT_TEMPLATE = """CONTENT: \n{page_content}\nSOURCE: file_id='{file_id}', file_name='{filename}', page='{page}'"""

DOCUMENT_PROMPT = PromptTemplate(
    template=DOCUMENT_PROMPT_TEMPLATE,
    input_variables=["page_content", "page", "filename", "file_id"],
)

SEARCH_ENTIRE_DOCUMENT_TEMPLATE = """You are a detail oriented master researcher, and are running a search through a long document (split into chunks) and collecting information that will help answer some QUESTION(S).  Your job is to examine the provided DOCUMENT CHUNKS and find any information that may be relevant to the QUESTION(S).

Here is the current portion of the document you are looking at:
--- DOCUMENT CHUNKS ---
{previous_context}
{current_context}
--- DOCUMENT CHUNKS ---

Take a deep breath, and read the QUESTION(S) carefully.  If you find any information that may be of relevance to the QUESTION(S), be sure to include it in your response.

--- QUESTION(S) ---
{questions}
--- QUESTION(S) ---

If the DOCUMENT CHUNKS does not contain any information relevant to the QUESTION(S), please respond ONLY with: "NO RELEVANT INFORMATION".

IMPORTANT: Only return information from the DOCUMENT CHUNKS that may be relevant to the QUESTION(S), do not make your own judgments of the data, nor add any commentary.  Another AI will look at your work and answer the QUESTION(S) using the data you have provided.

In the past, you have made mistakes where you have missed information relevant to the QUESTION(S). So, please take it line-by-line, and carefully analyze and consider all the information in the DOCUMENT CHUNKS before providing a response.

AI: Sure! Here is the information that I have found that may be relevant to the QUESTION(S), or "NO RELEVANT INFORMATION" if there is no information that could possibly be used to answer to the QUESTION(S):
"""
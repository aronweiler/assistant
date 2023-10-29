from langchain.prompts import PromptTemplate

QUESTION_PROMPT_TEMPLATE = """Use the following portion(s) of a long document to see if any of the text is relevant to answer the question. 
Return any relevant text verbatim, including citations, if any.

--- BEGIN EXAMPLE 1 ---
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
Aron Weiler held the position of Senior Software Engineer at OFFICETOOL.COM, INC. from Sept 2002 to Jul 2004.

Here are some details about the position:

- Joined in September 2002 as a contractor, leveraging expertise in Microsoft's .NET programming languages.
- Transitioned to a full-time employee role.
- Managed multiple projects with cross-functional teams of programmers.
- Independently developed applications from inception to completion.
- Conducted training sessions for fellow developers on the .NET architecture.
- Assisted in testing and maintenance of both new and existing applications.

Source: *[aron weiler resume.pdf (Page 5)](/files?file_id=1234&page=5)*
--- END EXAMPLE 1 ---

--- BEGIN EXAMPLE 2 ---
CONTENT: 
class LLMType(Enum):
    '''Enum for the type of prompt to use.'''

    LLAMA2 = "llama2"
    OPENAI = "openai"
    LUNA = "luna"
SOURCE: file_id='1234', file_name='my_code_file.py', line='17' 

CONTENT: 
# Abstract class for destinations
class DestinationBase(ABC):
    @abstractmethod
    def run(self, input: str, collection_id: str = None, llm_callbacks: list = [], agent_callbacks: list = []):
        pass
SOURCE: file_id='1234', file_name='my_code_file.py', line='5' 

Question: What abstract class is used for destinations?

Relevant text, if any, including document and page citations (in Markdown format):
The abstract class used for destinations is `DestinationBase`, which is found in the `my_code_file.py` file.

Source: *[my_code_file.py (line 5)](/files?file_id=1234&line=5)*
--- END EXAMPLE 2 ---

{summaries}

Question: {question}

Relevant text, if any, including document and page/line citations (in Markdown format):
"""

QUESTION_PROMPT = PromptTemplate(
    template=QUESTION_PROMPT_TEMPLATE, input_variables=["summaries", "question"]
)

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
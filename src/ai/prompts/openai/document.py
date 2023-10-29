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

SEARCH_ENTIRE_DOCUMENT_TEMPLATE = """You are part of a loop that I am running to search through a long document (split into chunks) and collect information that will help me answer some question(s).  Your job is to find any information that may be relevant to the question(s).

Below is a scratchpad that we will use to attempt to answer the questions(s) after we look at all of the documents.  This is for you to store relevant information. Please take what is already in the scratchpad and ADD any information you find that is relevant to the question(s).  If you do not find any relevant information, please return the scratchpad without any modification.  You should never remove information from the scratchpad.

--- SCRATCHPAD ---
{existing_information}
--- SCRATCHPAD ---

The current context is the current portion of the document that is being searched. You should search through the current context to find information relevant to the question(s).
--- CURRENT CONTEXT ---
{previous_context}
{current_context}
--- CURRENT CONTEXT ---

Take a deep breath, and read the question(s) carefully.  

Find any information in the context related to the question(s).  
{questions}

If you find any information that may be of relevance to the question(s), be sure to include it in your response (updated scratchpad).

Slow down and re-read the current context.  Does the current context contain any information relevant to the question(s)? If so, please update the scratchpad in your response, adding the new information you have discovered that can help construct an ultimate answer.  

If the current context does not contain any information relevant to the question, please respond only by returning the data in the scratchpad without any modification.

IMPORTANT: Make sure that you do not duplicate information in the scratchpad.  If you find information that is already in the scratchpad, please do not add it again.  

AI: Sure! Here is my updated scratchpad, where I have only added information relevant to the question(s) (if I didn't find anything, I will return the scratchpad without any modification):
--- SCRATCHPAD ---
"""
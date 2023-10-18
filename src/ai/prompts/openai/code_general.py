from langchain.prompts import PromptTemplate

CODE_PROMPT_TEMPLATE = """CONTENT: \n{page_content}\nSOURCE: file_id='{file_id}', file_name='{filename}, line={start_line}'"""

CODE_PROMPT = PromptTemplate(
    template=CODE_PROMPT_TEMPLATE,
    input_variables=["page_content", "filename", "file_id", "start_line"],
)
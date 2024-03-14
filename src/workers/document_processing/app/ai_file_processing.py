import json
import logging
from typing import List

from src.shared.ai.prompts.prompt_manager import PromptManager
from src.shared.configuration.model_configuration import ModelConfiguration
from src.shared.database.models.documents import Documents
from src.shared.database.models.user_settings import UserSettings
from src.shared.ai.prompts.prompt_models.code_details_extraction import (
    CodeDetailsExtractionInput,
    CodeDetailsExtractionOutput,
)
from src.shared.ai.prompts.prompt_models.document_summary import (
    DocumentChunkSummaryInput,
    DocumentSummaryOutput,
    DocumentSummaryRefineInput,
)
from src.shared.ai.prompts.prompt_models.question_generation import (
    QuestionGenerationInput,
    QuestionGenerationOutput,
)
from src.shared.ai.prompts.query_helper import QueryHelper
from src.shared.ai.utilities.llm_helper import get_llm


def generate_keywords_and_descriptions_from_code_file(
    user_id: int,
    code: str,
) -> CodeDetailsExtractionOutput:
    llm = get_llm(
        get_file_ingestion_model_configuration(user_id),
        tags=["generate_keywords_and_descriptions_from_code_file"],
        streaming=False,
    )

    input_object = CodeDetailsExtractionInput(code=code)

    result = get_query_helper(user_id).query_llm(
        llm=llm,
        prompt_template_name="CODE_DETAILS_EXTRACTION_TEMPLATE",
        input_class_instance=input_object,
        output_class_type=CodeDetailsExtractionOutput,
        timeout=30000,
    )

    return result


# Required by the Jarvis UI when ingesting files
def generate_detailed_document_chunk_summary(
    user_id: int,
    chunk_text: str,
) -> str:
    llm = get_llm(
        get_file_ingestion_model_configuration(user_id),
        tags=["generate_detailed_document_chunk_summary"],
        streaming=False,
    )

    input_object = DocumentChunkSummaryInput(chunk_text=chunk_text)

    result = get_query_helper(user_id).query_llm(
        llm=llm,
        prompt_template_name="DETAILED_DOCUMENT_CHUNK_SUMMARY_TEMPLATE",
        input_class_instance=input_object,
        output_class_type=DocumentSummaryOutput,
    )

    return result.summary


# Required by the Jarvis UI when generating questions for ingested files
def create_summary_and_chunk_questions(
    user_id: int, text: str, number_of_questions: int = 5
) -> List:    
    llm = get_llm(
        get_file_ingestion_model_configuration(user_id),
        tags=["generate_chunk_questions"],
        streaming=False,
    )

    input_object = QuestionGenerationInput(
        document_text=text, number_of_questions=number_of_questions
    )

    result = get_query_helper(user_id).query_llm(
        llm=llm,
        prompt_template_name="CHUNK_QUESTIONS_TEMPLATE",
        input_class_instance=input_object,
        output_class_type=QuestionGenerationOutput,
    )

    return result


def generate_detailed_document_summary(
    user_id: int, target_file_id: int, collection_id
) -> str:
    llm = get_llm(
        get_file_ingestion_model_configuration(user_id),
        tags=["retrieval-augmented-generation-ai"],
        streaming=False,
    )

    documents = Documents()
    file = documents.get_file(target_file_id)

    # Is there a summary already?  If so, return that instead of re-running the summarization.
    if file.file_summary and file.file_summary != "":
        return file.file_summary

    # Get the document chunks
    document_chunks = documents.get_document_chunks_by_file_id(
        target_file_id=target_file_id
    )

    existing_summary = "No summary yet!"

    # Are there already document chunk summaries?
    for chunk in document_chunks:
        if not chunk.document_text_has_summary:
            # Summarize the chunk
            summary_chunk = generate_detailed_document_chunk_summary(
                chunk_text=chunk.document_text, llm=llm
            )
            documents.set_document_text_summary(chunk.id, summary_chunk, collection_id)

        input_object = DocumentSummaryRefineInput(
            text=chunk.document_text, existing_summary=existing_summary
        )

        result = get_query_helper(user_id).query_llm(
            llm=llm,
            prompt_template_name="DOCUMENT_REFINE_TEMPLATE",
            input_class_instance=input_object,
            output_class_type=DocumentSummaryOutput,
        )

        existing_summary = result.summary

    # Put the summary into the DB so we don't have to re-run this.
    documents.update_file_summary_and_class(
        file_id=file.id,
        summary=existing_summary,
        classification=file.file_classification,
    )

    return existing_summary


def get_file_ingestion_model_configuration(user_id):
    user_settings = UserSettings()
    file_ingestion_model_configuration = ModelConfiguration(
        **json.loads(
            user_settings.get_user_setting(
                user_id,
                "file_ingestion_model_configuration",
                default_value=ModelConfiguration.default().model_dump_json(),
            ).setting_value
        )
    )

    return file_ingestion_model_configuration


def get_query_helper(user_id: int):
    prompt_manager = PromptManager(
        llm_type=get_file_ingestion_model_configuration(user_id).llm_type
    )
    return QueryHelper(prompt_manager=prompt_manager)

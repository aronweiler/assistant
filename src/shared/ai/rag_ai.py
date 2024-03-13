import json
import logging
from uuid import UUID
from typing import List

from langchain.agents import AgentExecutor

from src.shared.configuration.model_configuration import (
    ModelConfiguration,
)

from src.shared.ai.prompts.prompt_models.code_details_extraction import (
    CodeDetailsExtractionInput,
    CodeDetailsExtractionOutput,
)
from src.shared.ai.prompts.prompt_models.conversation_summary import (
    ConversationSummaryInput,
    ConversationSummaryOutput,
)
from src.shared.ai.prompts.prompt_models.conversational import (
    ConversationalInput,
    ConversationalOutput,
)
from src.shared.ai.prompts.prompt_models.document_summary import (
    DocumentChunkSummaryInput,
    DocumentSummaryOutput,
)
from src.shared.ai.prompts.prompt_models.question_generation import (
    QuestionGenerationInput,
    QuestionGenerationOutput,
)
from src.shared.ai.prompts.query_helper import QueryHelper
from src.shared.ai.conversations.conversation_manager import ConversationManager
from src.shared.ai.utilities.llm_helper import get_llm
from src.shared.ai.prompts.prompt_manager import PromptManager
from src.shared.ai.utilities.system_info import get_system_information
from src.shared.ai.agents.general.generic_tools_agent import GenericToolsAgent
from src.shared.database.models.user_settings import UserSettings
from src.shared.database.models.users import Users
from src.shared.ai.tools.documents.document_tool import DocumentTool
from src.shared.ai.tools.tool_manager import ToolManager


# Constants for default penalties
DEFAULT_FREQUENCY_PENALTY = 0.0
DEFAULT_PRESENCE_PENALTY = 0.6
DEFAULT_AGENT_TIMEOUT = 300


class RetrievalAugmentedGenerationAI:
    """A class representing a Retrieval Augmented Generation AI.

    This AI integrates a language model with additional tools and agents to provide
    enhanced conversational capabilities.
    """

    def __init__(
        self,
        configuration,
        conversation_id: UUID,
        user_email: str,
        prompt_manager: PromptManager,
        streaming: bool = False,
        override_memory=None,
        model_configuration_name: str = "jarvis_ai_model_configuration",
    ):
        if conversation_id is None or user_email is None:
            raise ValueError("conversation_id and user_email cannot be None")

        self.configuration = configuration
        self.streaming = streaming
        self.prompt_manager = prompt_manager

        user = Users().get_user_by_email(user_email)
        user_settings = UserSettings()

        # Special case
        default_jarvis_model = ModelConfiguration.default()
        # Ensure that the main model uses conversation history if its never been used before
        default_jarvis_model.uses_conversation_history = True
        default_jarvis_model.max_conversation_history_tokens = 16384

        self.jarvis_ai_model_configuration = ModelConfiguration(
            **json.loads(
                user_settings.get_user_setting(
                    user.id,
                    model_configuration_name,
                    default_value=default_jarvis_model.model_dump_json(),
                ).setting_value
            )
        )

        self.file_ingestion_model_configuration = ModelConfiguration(
            **json.loads(
                user_settings.get_user_setting(
                    user.id,
                    "file_ingestion_model_configuration",
                    default_value=ModelConfiguration.default().model_dump_json(),
                ).setting_value
            )
        )

        # Set up the conversation manager
        self.conversation_manager = ConversationManager(
            conversation_id=conversation_id,
            user_email=user_email,
            prompt_manager=self.prompt_manager,
            max_conversation_history_tokens=self.jarvis_ai_model_configuration.max_conversation_history_tokens,
            uses_conversation_history=self.jarvis_ai_model_configuration.uses_conversation_history,
            override_memory=override_memory,
        )

        self.query_helper = QueryHelper(prompt_manager=self.prompt_manager)

        # Initialize the tool manager and load the available tools
        self.tool_manager = ToolManager(
            configuration=self.configuration,
            conversation_manager=self.conversation_manager,
        )

    def create_agent(self, agent_timeout: int = 300, max_iterations: int = 25):
        tools = self.tool_manager.get_enabled_tools()

        agent = GenericToolsAgent(
            model_configuration=self.jarvis_ai_model_configuration,
            conversation_manager=self.conversation_manager,
            tool_manager=self.tool_manager,
            tools=tools,
            streaming=self.streaming,
        )

        agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=[tool.structured_tool for tool in tools],
            verbose=True,
            max_execution_time=agent_timeout,  # early_stopping_method="generate" <- this is not supported, but somehow in their docs
            max_iterations=max_iterations,
        )

        agent_executor.return_intermediate_steps = True

        agent_executor.callbacks = self.conversation_manager.agent_callbacks

        return agent_executor

    def query(
        self,
        query: str,
        collection_id: int = None,
        kwargs: dict = {},
        ai_mode: str = None,
    ):
        # Set the document collection id on the conversation manager
        self.conversation_manager.collection_id = collection_id

        # Set the kwargs on the conversation manager (this is search params, etc.)
        self.conversation_manager.tool_kwargs = kwargs

        # Ensure we have a summary / title for the chat
        logging.debug("Checking to see if summary exists for this chat")
        self.check_summary(query=query)

        if not ai_mode:
            # Get the AI mode setting
            ai_mode = self.conversation_manager.get_user_setting(
                setting_name="ai_mode", default_value="auto"
            ).setting_value

        if ai_mode.lower().startswith("conversation"):
            logging.debug("Running chain in 'Conversation Only' mode")
            output = self.run_chain(
                query=query,
                kwargs=kwargs,
            )
        elif ai_mode.lower().startswith("auto"):
            # Run the agent
            logging.debug("Running agent in 'Auto' mode")
            results = self.run_agent(query=query, kwargs=kwargs)

            output = results["output"]

        # if output is a list, collapse it into a single string
        if isinstance(output, list):
            output = "\n".join([str(o) for o in output])

        # Adding this after the run so that the agent can't see it in the history
        self.conversation_manager.conversation_token_buffer_memory.save_context(
            inputs={"input": query}, outputs={"output": output}
        )

        logging.debug(output)
        logging.debug("Added results to chat memory")

        return output

    def run_chain(self, query: str, kwargs: dict = {}):
        llm = get_llm(
            self.jarvis_ai_model_configuration,
            tags=["conversational-ai"],
            callbacks=self.conversation_manager.llm_callbacks,
            streaming=True,
            model_kwargs={
                "frequency_penalty": self.configuration["jarvis_ai"].get(
                    "frequency_penalty", DEFAULT_FREQUENCY_PENALTY
                ),
                "presence_penalty": self.configuration["jarvis_ai"].get(
                    "presence_penalty", DEFAULT_PRESENCE_PENALTY
                ),
            },
        )

        input_object = ConversationalInput(
            system_prompt="You are a friendly AI who's purpose it is to engage a user in conversation.  Try to mirror their emotional state, and answer their questions.  If you don't know the answer, don't make anything up, just say you don't know.",
            user_query=query,
            user_name=self.conversation_manager.user_name,
            user_email=self.conversation_manager.user_email,
            chat_history=self.conversation_manager.get_chat_history_prompt(),
            system_information=get_system_information(
                self.conversation_manager.user_location
            ),
        )

        result = self.query_helper.query_llm(
            llm=llm,
            prompt_template_name="CONVERSATIONAL_TEMPLATE",
            input_class_instance=input_object,
            output_class_type=ConversationalOutput,
        )

        return result.answer

    def run_agent(self, query: str, kwargs: dict = {}):
        timeout = kwargs.get("agent_timeout", 300)
        max_iterations = kwargs.get("max_iterations", 25)
        evaluate_response = kwargs.get("evaluate_response", False)
        re_planning_threshold = kwargs.get("re_planning_threshold", 0.5)
        rephrase_answer_instructions = kwargs.get("rephrase_answer_instructions", None)

        logging.debug(f"Creating agent with {timeout} second timeout")
        agent = self.create_agent(agent_timeout=timeout, max_iterations=max_iterations)

        # Run the agent
        logging.debug("Running agent")

        agent_results = agent.invoke(
            {
                "input": query,
                "system_information": get_system_information(
                    self.conversation_manager.user_location
                ),
                "user_name": self.conversation_manager.user_name,
                "user_email": self.conversation_manager.user_email,
                "evaluate_response": evaluate_response,
                "re_planning_threshold": re_planning_threshold,
                "rephrase_answer_instructions": rephrase_answer_instructions or "",
            }
        )

        return agent_results

    def check_summary(self, query):
        if self.conversation_manager.conversation_needs_summary:
            logging.debug("Interaction needs summary, generating one now")
            conversation_summary = self.generate_conversation_summary(query=query)

            self.conversation_manager.set_conversation_summary(conversation_summary)
            self.conversation_manager.conversation_needs_summary = False
            logging.debug(f"Generated summary: {conversation_summary}")

    def generate_conversation_summary(self, query: str):
        llm = get_llm(
            self.jarvis_ai_model_configuration,
            tags=["conversation-summary-ai"],
            streaming=False,
        )

        summary_input = ConversationSummaryInput(
            user_query=query,
        )

        summary_output = self.query_helper.query_llm(
            llm=llm,
            prompt_template_name="SUMMARIZE_FOR_LABEL_TEMPLATE",
            input_class_instance=summary_input,
            output_class_type=ConversationSummaryOutput,
        )

        return summary_output.summary

    def generate_keywords_and_descriptions_from_code_file(
        self, code: str
    ) -> CodeDetailsExtractionOutput:
        llm = get_llm(
            self.file_ingestion_model_configuration,
            tags=["generate_keywords_and_descriptions_from_code_file"],
            streaming=False,
        )

        input_object = CodeDetailsExtractionInput(code=code)

        result = self.query_helper.query_llm(
            llm=llm,
            prompt_template_name="CODE_DETAILS_EXTRACTION_TEMPLATE",
            input_class_instance=input_object,
            output_class_type=CodeDetailsExtractionOutput,
            timeout=30000,
        )

        return result

    # Required by the Jarvis UI when ingesting files
    def generate_detailed_document_chunk_summary(
        self,
        chunk_text: str,
    ) -> str:
        llm = get_llm(
            self.file_ingestion_model_configuration,
            tags=["generate_detailed_document_chunk_summary"],
            streaming=False,
        )

        input_object = DocumentChunkSummaryInput(chunk_text=chunk_text)

        result = self.query_helper.query_llm(
            llm=llm,
            prompt_template_name="DETAILED_DOCUMENT_CHUNK_SUMMARY_TEMPLATE",
            input_class_instance=input_object,
            output_class_type=DocumentSummaryOutput,
        )

        return result.summary

    # Required by the Jarvis UI when generating questions for ingested files
    def create_summary_and_chunk_questions(
        self, text: str, number_of_questions: int = 5
    ) -> List:
        llm = get_llm(
            self.file_ingestion_model_configuration,
            tags=["generate_chunk_questions"],
            streaming=False,
        )

        input_object = QuestionGenerationInput(
            document_text=text, number_of_questions=number_of_questions
        )

        result = self.query_helper.query_llm(
            llm=llm,
            prompt_template_name="CHUNK_QUESTIONS_TEMPLATE",
            input_class_instance=input_object,
            output_class_type=QuestionGenerationOutput,
        )

        return result

    def generate_detailed_document_summary(
        self,
        file_id: int,
    ) -> str:
        llm = get_llm(
            self.file_ingestion_model_configuration,
            tags=["retrieval-augmented-generation-ai"],
            streaming=False,
        )

        document_tool = DocumentTool(self.configuration, self.conversation_manager)
        document_summary = document_tool.summarize_entire_document_with_llm(
            llm, file_id
        )

        return document_summary

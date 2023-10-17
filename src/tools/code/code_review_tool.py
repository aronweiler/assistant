import sys
import os
import logging
from typing import List

from langchain.chains.llm import LLMChain
from langchain.base_language import BaseLanguageModel
from langchain.chains import (
    RetrievalQAWithSourcesChain,
    StuffDocumentsChain,
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.db.models.conversations import SearchType
from src.db.models.documents import Documents
from src.ai.interactions.interaction_manager import InteractionManager

from src.utilities.token_helper import num_tokens_from_string

from src.db.models.pgvector_retriever import PGVectorRetriever

from src.ai.llm_helper import get_prompt

from src.tools.code.code_dependency import CodeDependency
from src.tools.code.code_tool import CodeTool

from src.integrations.gitlab.gitlab_issue_creator import GitlabIssueCreator
from src.integrations.gitlab.gitlab_file_retriever import GitlabFileRetriever

from src.integrations.github.github_file_retriever import GitHubFileRetriever


# import logging
# import json
# from uuid import UUID
# from typing import List

# from langchain.base_language import BaseLanguageModel

from langchain.agents.structured_chat.output_parser import (
    StructuredChatOutputParserWithRetries,
)

from langchain.memory.readonly import ReadOnlySharedMemory

from langchain.tools import StructuredTool

from langchain.agents import initialize_agent, AgentType

from src.configuration.assistant_configuration import (
    # RetrievalAugmentedGenerationConfiguration,
    ModelConfiguration,
)

# from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm, get_prompt
from src.ai.system_info import get_system_information

from src.tools.documents.document_tool import DocumentTool

# from src.tools.documents.spreadsheet_tool import SpreadsheetsTool
# from src.tools.code.code_tool import CodeTool

# from src.ai.agents.code.stubbing_agent import Stubber
# from src.ai.agents.code.code_review_agent import CodeReviewer


class CodeReviewTool:
    source_control_to_file_retriever_map: dict = {"gitlab": GitlabFileRetriever, "github": GitHubFileRetriever}
    source_control_to_issue_creator_map: dict = {"gitlab": GitlabIssueCreator, "github": None}

    def __init__(self, configuration, interaction_manager: InteractionManager, llm: BaseLanguageModel):
        self.configuration = configuration
        self.interaction_manager = interaction_manager
        self.llm = llm

        self.code_tool = CodeTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
            llm=self.llm,
        )

        self.agent = self.create_agent()

    def create_agent(self, agent_timeout: int = 300):
        logging.debug("Setting human message template")
        human_message_template = get_prompt(
            self.configuration.model_configuration.llm_type, "AGENT_TEMPLATE"
        )

        logging.debug("Setting memory")
        memory = ReadOnlySharedMemory(
            memory=self.interaction_manager.conversation_token_buffer_memory
        )

        logging.debug("Setting suffix")
        suffix = get_prompt(
            self.configuration.model_configuration.llm_type, "TOOLS_SUFFIX"
        )

        logging.debug("Setting format instructions")
        format_instructions = get_prompt(
            self.configuration.model_configuration.llm_type,
            "TOOLS_FORMAT_INSTRUCTIONS",
        )

        # This is a problem with langchain right now- hopefully it resolves soon, because the StructuredChatOutputParserWithRetries is crap without the llm
        try:
            output_parser = StructuredChatOutputParserWithRetries.from_llm(llm=self.llm)
        except Exception as e:
            logging.error(f"Could not create output parser: {e}")
            logging.warning("Falling back to default output parser")
            output_parser = StructuredChatOutputParserWithRetries()

        logging.debug("Setting agent kwargs")
        agent_kwargs = {
            "suffix": suffix,
            "format_instructions": format_instructions,
            "output_parser": output_parser,
            "input_variables": [
                "input",
                "loaded_documents",
                "chat_history",
                "agent_scratchpad",
                "system_information",
            ],
            "verbose": True,
        }

        logging.debug(f"Creating agent with kwargs: {agent_kwargs}")
        agent = initialize_agent(
            tools=self.get_tools(),
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            human_message_template=human_message_template,
            memory=memory,
            agent_kwargs=agent_kwargs,
            max_execution_time=agent_timeout,
            # early_stopping_method="generate" <- this is not supported, but somehow in their docs
        )

        return agent

    def ingest_source_code_file_from_url(self, url):
        source_control_provider = os.getenv("SOURCE_CONTROL_PROVIDER", "GitHub")
        file_retriever = self.source_control_to_file_retriever_map[source_control_provider.lower()]
        if not file_retriever:
            return f"Source control provider {source_control_provider} does not support file retrieval"

        file_retriever = file_retriever(
            source_control_url=os.getenv("source_control_url"),
            source_control_pat=os.getenv("source_control_pat"),
        )

        return file_retriever.retrieve_file_data(url=url)

    def create_code_review_issue_tool(
        self,
        project_id: int,
        ref: str,
        source_code_file_href: str,
        source_code_file_path: str,
        review_data: dict,
    ):
        """
        Creates an issue containing the code review for a single reviewed file,on the source code control system specified

        # Args:
        #     source_code_file_data: A dictionary containing the project ID, file URL, file relative path, ref name, file contents
        #     review_data: A python dictionary containing the code review data to create the issue from
        """
        source_control_provider = os.getenv("SOURCE_CONTROL_PROVIDER", "GitHub")
        issue_creator = self.source_control_to_issue_creator_map[source_control_provider.lower()]
        if not issue_creator:
            return f"Source control provider {source_control_provider} does not support issue creation"
        
        issue_creator = issue_creator(
            source_control_url=os.getenv("source_control_url"),
            source_control_pat=os.getenv("source_control_pat"),
        )

        result = issue_creator.generate_issue(
            project_id=project_id,
            ref=ref,
            source_code_file_loc=source_code_file_path,
            source_code_file_href=source_code_file_href,
            review_data=review_data,
        )

        return f"Successfully created issue at {result['url']}"

    def get_tools(self) -> list[StructuredTool]:
        return [
            StructuredTool.from_function(
                func=self.code_tool.get_code_details,
            ),
            StructuredTool.from_function(
                func=self.code_tool.get_code_structure,
            ),
            StructuredTool.from_function(
                func=self.code_tool.get_dependency_graph,
            ),
        ]

    def conduct_code_review_from_url(self, target_url: str, additional_instructions: str = None):
        """
        Conducts a code review for the specified file from a given target URL

        Args:
            target_url: The URL of the file to code review
        """
        if additional_instructions:
            additional_instructions = f"\n--- ADDITIONAL INSTRUCTIONS ---\n{additional_instructions}\n--- ADDITIONAL INSTRUCTIONS ---\n"
        else:
            additional_instructions = ""
        
        file_info = self.ingest_source_code_file_from_url(url=target_url)

        file_data = file_info["file_content"]

        # TODO combine with other conduct code review function for common pieces
        max_code_review_token_count = self.interaction_manager.tool_kwargs.get(
            "max_code_review_token_count", 5000
        )
        if num_tokens_from_string(file_data) > max_code_review_token_count:
            return "File is too large to be code reviewed. Adjust max code review tokens, or refactor your code."

        code = file_data.splitlines()
        for line_num, line in enumerate(code):
            code[line_num] = f"{line_num}: {line}"

        code_metadata = {
            "project_id": file_info["project_id"],
            "url": file_info["url"],
            "ref": file_info["ref"],
            "file_path": file_info["file_path"],
        }

        code_review_prompt = get_prompt(
            self.configuration.model_configuration.llm_type, "CODE_REVIEW_TEMPLATE"
        ).format(
            code_summary="",
            code_dependencies="",
            code=code,
            code_metadata=code_metadata,
            additional_instructions=additional_instructions
        )

        results = self.llm.predict(code_review_prompt)

        return results

    def conduct_code_review_from_file_id(self, target_file_id:int, additional_instructions: str = None):
        """
        Conducts a code review for the specified file

        Args:
            target_file_id: The id of the file to conduct a code review on
        """
        
        if additional_instructions:
            additional_instructions = f"\n--- ADDITIONAL INSTRUCTIONS ---\n{additional_instructions}\n--- ADDITIONAL INSTRUCTIONS ---\n"
        else:
            additional_instructions = ""
        
        documents = Documents()

        # Get the list of documents
        file_model = documents.get_file(
            file_id=target_file_id,
        )

        if file_model.file_classification.lower() != "code":
            return "File is not code. Please select a code file to conduct a code review on, or use a different tool."

        # Convert file data bytes to string
        file_data = file_model.file_data.decode("utf-8")

        max_code_review_token_count = self.interaction_manager.tool_kwargs.get(
            "max_code_review_token_count", 5000
        )
        if num_tokens_from_string(file_data) > max_code_review_token_count:
            return "File is too large to be code reviewed. Adjust max code review tokens, or refactor your code."

        code = file_data.splitlines()
        for line_num, line in enumerate(code):
            code[line_num] = f"{line_num}: {line}"

        dependencies = self.code_tool.get_dependency_graph(
            target_file_id=target_file_id
        )
        dependencies = "\n----- CODE DEPENDENCIES -----\n" + dependencies + "\n----- CODE DEPENDENCIES -----\n"

        document_tool = DocumentTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
            llm=self.llm,
        )

        summary = document_tool.summarize_entire_document(target_file_id=target_file_id)
        summary = "\n--- CODE SUMMARY ---\n" + summary + "\n--- CODE SUMMARY ---\n"

        code_review_prompt = get_prompt(
            self.configuration.model_configuration.llm_type, "CODE_REVIEW_TEMPLATE"
        ).format(
            code_summary=summary,
            code_dependencies=dependencies,
            code=code,
            code_metadata={"filename": file_model.file_name},
            additional_instructions=additional_instructions
        )

        logging.debug("Running agent")
        results = self.agent.run(
            input=code_review_prompt,
            system_information=get_system_information(
                self.interaction_manager.user_location
            ),
            user_name=self.interaction_manager.user_name,
            user_email=self.interaction_manager.user_email,
            loaded_documents="\n".join(
                self.interaction_manager.get_loaded_documents_for_reference()
            ),
            # callbacks=agent_callbacks,
        )
        logging.debug("Agent finished running")

        return results

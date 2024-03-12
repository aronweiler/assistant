from typing import List
from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.prompts.prompt_models.code_review import CodeReviewInput, CodeReviewOutput
from src.ai.utilities.llm_helper import get_llm
from src.ai.prompts.query_helper import QueryHelper
from src.ai.tools.tool_registry import register_tool, tool_class
from src.configuration.model_configuration import ModelConfiguration
from src.db.models.documents import Documents
from src.db.models.user_settings import UserSettings
from src.tools.code.code_retriever_tool import CodeRetrieverTool


@tool_class
class CodeReviewTool:
    def __init__(self, configuration, conversation_manager: ConversationManager):
        self.configuration = configuration
        self.conversation_manager = conversation_manager

    @register_tool(
        display_name="Perform a Code Review",
        description="Perform a code review on a loaded document, a URL, or a repository file.",
        additional_instructions="Use this tool for conducting a code review on a loaded document, a URL, or a repository file. Make sure to understand and pass the correct argument (either `loaded_document_id`, `url`, or `repository_file_id`) based on the user's request.  If the user specifies a URL, do not use the loaded repository, instead pass the URL in here.  Use the additional_instructions field to pass additional code review instructions from the user, if any.",
        category="Code",
        requires_llm=True,
    )
    def conduct_code_review(
        self,
        loaded_document_id: int = None,
        url: str = None,
        repository_file_id: int = None,
        additional_instructions: str = None,
    ) -> dict:
        if loaded_document_id:
            documents = Documents()
            file_model = documents.get_file(file_id=loaded_document_id)
            code = documents.get_file_data(file_model.id).decode("utf-8")
            metadata = {"filename": file_model.file_name, "type": "file"}
        elif url:
            file_info = CodeRetrieverTool(
                configuration=self.configuration,
                conversation_manager=self.conversation_manager,
            ).retrieve_source_code(url=url)
            if file_info["type"] != "diff":
                code = file_info.pop("file_content")

            metadata = file_info
        elif repository_file_id:
            code_file = self.conversation_manager.code_helper.get_code_file_by_id(
                repository_file_id
            )
            code = code_file.code_file_content
            metadata = {"filename": code_file.code_file_name, "type": "file"}
        else:
            raise ValueError(
                "A valid loaded_document_id, url, or repository_file_id must be provided."
            )

        # Get the setting for the tool model
        tool_model_configuration = UserSettings().get_user_setting(
            user_id=self.conversation_manager.user_id,
            setting_name=f"{self.conduct_code_review.__name__}_model_configuration",
            default_value=ModelConfiguration.default().model_dump(),
        ).setting_value

        llm = get_llm(
            model_configuration=tool_model_configuration,
            streaming=True,
            callbacks=self.conversation_manager.agent_callbacks,
        )

        templates = self.get_active_code_review_templates(
            self.conduct_code_review.__name__
        )

        reviews = []

        if metadata["type"] == "diff":
            # Extract changes from metadata and remove 'changes' key from metadata.
            changes = file_info.pop("changes", None)

            for diff in changes:
                file_info["old_path"] = diff["old_path"]
                file_info["new_path"] = diff["new_path"]

                reviews.extend(
                    self._process_templates(
                        templates=templates,
                        metadata=file_info,
                        additional_instructions=additional_instructions,
                        code=diff["raw"],
                        llm=llm,
                    )
                )
        else:
            reviews.extend(
                self._process_templates(
                    templates=templates,
                    metadata=metadata,
                    additional_instructions=additional_instructions,
                    code=code,
                    llm=llm,
                )
            )

        return reviews

    def _perform_single_review(
        self,
        metadata,
        code,
        llm,
        template_instructions="",
        additional_instructions="",
    ) -> dict:
        # Split the file data into lines and prepend line numbers for clarity.
        code_with_line_numbers = "\n".join(
            [
                f"{line_num + 1}: {line}"
                for line_num, line in enumerate(code.splitlines())
            ]
        )

        # Prepare input for the language model.
        input_data = CodeReviewInput(
            code_review_instructions=template_instructions,
            code=code_with_line_numbers,
            additional_instructions=additional_instructions,
            code_metadata=metadata,
        )

        # Query the language model.
        query_helper = QueryHelper(self.conversation_manager.prompt_manager)
        result: CodeReviewOutput = query_helper.query_llm(
            llm=llm,
            input_class_instance=input_data,
            prompt_template_name="CODE_REVIEW_INSTRUCTIONS_TEMPLATE",
            output_class_type=CodeReviewOutput,
        )

        # Process the output.
        review_results = {
            "language": result.language,
            "metadata": result.metadata,
            "thoughts": result.thoughts,
            "comments": [
                {
                    "start": comment.start,
                    "end": comment.end,
                    "comment": comment.comment,
                    "needs_change": comment.needs_change,
                    "original_code_snippet": comment.original_code_snippet,
                    "suggested_code_snippet": comment.suggested_code_snippet,
                }
                for comment in result.comments
            ],
        }

        return review_results

    def get_active_code_review_templates(self, tool_name: str) -> List[dict]:
        """
        Retrieves active code review templates based on the provided tool name.
        """

        # Access additional settings specific to the tool from configuration.
        additional_settings = self.configuration["tool_configurations"][tool_name][
            "additional_settings"
        ]

        templates = []
        template_checks = {
            "enable_code_security_examination": "Security",
            "enable_code_performance_examination": "Performance",
            "enable_code_memory_examination": "Memory",
            "enable_code_correctness_examination": "Correctness",
            "enable_code_maintainability_examination": "Maintainability",
            "enable_code_reliability_examination": "Reliability",
        }

        for setting, description in template_checks.items():
            if additional_settings[f"{setting}"]["value"]:
                templates.append(
                    {
                        "name": f"{setting.lstrip('enable_').upper()}_TEMPLATE",
                        "description": description,
                    }
                )

        return templates

    def _process_templates(
        self,
        templates,
        metadata: dict,
        additional_instructions: str,
        code: str,
        llm,
    ):
        if not templates or len(templates) == 0:
            # process the additional instructions on their own
            review = self._perform_single_review(
                metadata=metadata,
                code=code,
                llm=llm,
                additional_instructions=additional_instructions,
            )

            return [review]

        else:
            # Iterate over each template and perform a review using the language model.
            review_results = []
            for template in templates:
                template_instructions = self.conversation_manager.prompt_manager.get_prompt_by_template_name(
                    template["name"]
                )

                review = self._perform_single_review(
                    metadata=metadata,
                    code=code,
                    llm=llm,
                    template_instructions=template_instructions,
                    additional_instructions=additional_instructions,
                )

                # Append results from current template's review.
                # Note: This is not currently used anywhere- the ultimate result of this tool is just the final code
                # However, this is here so that we can do something with the data generated by each of the steps in the future.
                review_results.append(review)

            return review_results

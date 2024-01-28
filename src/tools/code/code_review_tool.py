from typing import List
from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.prompts.prompt_models.code_review import CodeReviewInput, CodeReviewOutput
from src.ai.llm_helper import get_tool_llm
from src.ai.prompts.query_helper import QueryHelper
from src.ai.tools.tool_registry import register_tool, tool_class
from src.tools.code.code_retriever_tool import CodeRetrieverTool


@tool_class
class CodeReviewTool:
    def __init__(self, configuration, conversation_manager: ConversationManager):
        self.configuration = configuration
        self.conversation_manager = conversation_manager

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

    @register_tool(
        display_name="Conduct Code Review from URL",
        help_text="Conducts a code review from a specified URL.",
        requires_documents=False,
        description="Performs a code review of a specified code file or pull request / merge request located at a URL.",
        additional_instructions="Use this tool for conducting a code review of a file located at a URL. Use the additional_instructions field to pass any code review additional instructions from the user, if any.",
    )
    def conduct_code_review_from_url(
        self, target_url, additional_instructions: str = None
    ) -> dict:
        # Get the code from the URL.
        retriever = CodeRetrieverTool()
        file_info = retriever.retrieve_source_code_from_url(url=target_url)

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.conduct_code_review_from_url.__name__,
            streaming=True,
            callbacks=self.conversation_manager.agent_callbacks,
        )

        templates = self.get_active_code_review_templates(
            self.conduct_code_review_from_url.__name__
        )

        reviews = []

        if file_info["type"] == "diff":
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
            content = file_info.pop("file_content")

            reviews.extend(
                self._process_templates(
                    templates=templates,
                    metadata=file_info,
                    additional_instructions=additional_instructions,
                    code=content,
                    llm=llm,
                )
            )

        return reviews

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

import sys
import os
from typing import Any, List, Tuple, Union

from langchain.base_language import BaseLanguageModel
from langchain.agents import Tool, AgentExecutor, BaseMultiActionAgent
from langchain.schema import AgentAction, AgentFinish
from langchain.tools import StructuredTool

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)

from src.tools.code.code_tool import CodeTool
from src.tools.documents.document_tool import DocumentTool
from src.tools.code.code_dependency import CodeDependency

from src.db.models.documents import Documents

from src.ai.interactions.interaction_manager import InteractionManager
from src.db.models.domain.file_model import FileModel

from src.ai.llm_helper import get_llm


class CodeReviewer:
    def __init__(
        self,
        llm: BaseLanguageModel,
        code_tool: CodeTool,
        document_tool: DocumentTool,
        interaction_manager: InteractionManager,
        callbacks: list = [],
    ) -> None:
        self.llm = llm
        self.interaction_manager = interaction_manager
        self.agent = CodeReviewAgent()
        self.callbacks = callbacks

        tools = [
            StructuredTool.from_function(
                func=code_tool.get_code_structure, callbacks=self.callbacks
            ),
            StructuredTool.from_function(
                func=code_tool.get_dependency_graph, callbacks=self.callbacks
            ),
            StructuredTool.from_function(
                func=document_tool.list_documents, callbacks=self.callbacks
            ),
        ]

        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent, tools=tools, verbose=True
        )

    def code_review(self, file_id: int):
        """Useful for code reviewing a specified file.

        Args:
            file_id: The id of the file to code review.
        """

        return self.agent_executor.run(
            file_id=file_id, collection_id=self.interaction_manager.collection_id
        )


class CodeReviewAgent(BaseMultiActionAgent):
    @property
    def input_keys(self):
        return ["file_id", "collection_id"]

    def plan(
        self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any
    ) -> Union[List[AgentAction], AgentFinish]:
        """Given input, decide what to do.

        Args:
            intermediate_steps: Steps the LLM has taken to date,
                along with observations
            **kwargs: User inputs.

        Returns:
            Action specifying what tool to use.
        """

        if not intermediate_steps:
            actions = []
            file_id = kwargs["file_id"]

            # Get the code structure for the file
            actions.append(
                AgentAction(
                    tool="get_code_structure",
                    tool_input={"target_file_id": file_id},
                    log=f"Getting the code structure for: {file_id}",
                )
            )

            # Get the dependency chain for the given file
            actions.append(
                AgentAction(
                    tool="get_dependency_graph",
                    tool_input={"target_file_id": file_id},
                    log=f"Getting dependency graph for file: {file_id}",
                )
            )

            return actions

        elif len(intermediate_steps) == 2:
            # We have the code structure and the dependency graph only
            get_code_structure = intermediate_steps[-2][1]
            code_dependency: CodeDependency = intermediate_steps[-1][1]

            # Call out to a function that prompts the llm to begin the code review
            # Use the code structure and the dependencies in the prompt asking where to start the code review
            # Utilize the same tool prompt / format as each of the code review chunks
            # The LLM should look at the available code, and then request details on a specific part of the code
            # E.g. "What is the purpose of the function: {function_name}?" Which would be translated into a get_code_details tool call

        elif intermediate_steps[-1][0].tool == "get_code_details":
            # The LLM requested this chunk of code
            get_code_details = intermediate_steps[-1][1]

            # This is where the results of the get_code_details tool call would be used to prompt the LLM to review the code
            # or to ask for more details about the code, or ultimately end the code review.
            # Each time the LLM is given code, we should also have it output the review of the code if possible-
            # e.g. if the code is a simple function, only return the review- no need to ask for more details on anything.
            # The results of the get_code_details call that got us here should be inserted into the existing prompt as "code"-
            # but the LLM needs to be able to tell if this code is given to provide context to something else its reviewing,
            # or if this code is the code to review.

        elif intermediate_steps[-1][0].tool == "review_code_snippet":
            # If the last thing the LLM did was to call the tool to document a snippet review, we need to store that (in the database?)
            # as a part of the code review for the file.

            # TODO: Define SnippetCodeReview- should be a class that stores the code snippet, the review, and generally the context of the review
            get_code_details: SnippetCodeReview = intermediate_steps[-1][1]

        return AgentFinish({"output": "done"}, log="Finished stubbing")

    async def aplan(
        self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any
    ) -> Union[List[AgentAction], AgentFinish]:
        """Given input, decided what to do.

        Args:
            intermediate_steps: Steps the LLM has taken to date,
                along with observations
            **kwargs: User inputs.

        Returns:
            Action specifying what tool to use.
        """

        raise NotImplementedError("Async plan not implemented.")

import sys
import os
from typing import Any, List, Tuple, Union

from langchain.agents import Tool, AgentExecutor, BaseMultiActionAgent
from langchain.schema import AgentAction, AgentFinish
from langchain.tools import StructuredTool

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)

from src.tools.documents.code_tool import CodeTool
from src.tools.documents.document_tool import DocumentTool
from src.tools.documents.code_dependency import CodeDependency

from src.db.models.documents import Documents

from src.ai.interactions.interaction_manager import InteractionManager
from src.db.models.domain.file_model import FileModel

# Create an basic agent that takes a single input, runs it through a tool, and returns the output


class Stubber:
    def __init__(
        self,
        code_tool: CodeTool,
        document_tool: DocumentTool,
        agent_callback,
        interaction_manager: InteractionManager,
    ) -> None:
        self.interaction_manager = interaction_manager
        self.agent = StubbingAgent()        

        tools = [
            StructuredTool.from_function(
                func=code_tool.code_structure, callbacks=[agent_callback]
            ),
            StructuredTool.from_function(
                func=code_tool.create_stub_code, callbacks=[agent_callback]
            ),
            StructuredTool.from_function(
                func=code_tool.get_dependency_graph, callbacks=[agent_callback]
            ),
            StructuredTool.from_function(
                func=document_tool.list_documents, callbacks=[agent_callback]
            ),
        ]

        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent, tools=tools, verbose=True
        )

    def create_stubs(self, file_id: int):
        """Create mocks / stubs for the dependencies of a given code file.  
        
        Use this when the user asks you to mock or stub out the dependencies for a given file.

        Args:
            file_id: The id of the file to create stubs for.
        """

        return self.agent_executor.run(
            file_id=file_id, collection_id=self.interaction_manager.collection_id
        )

class StubbingAgent(BaseMultiActionAgent):
    @property
    def input_keys(self):
        return ["file_id", "collection_id"]

    def plan(
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

        if not intermediate_steps:
            # Get the dependency chain for the given file

            return AgentAction(
                tool="get_dependency_graph",
                tool_input={
                    "target_file_id": kwargs["file_id"],
                    "collection_id": kwargs["collection_id"],
                },
                log=f"Getting dependency graph for file: {kwargs['file_id']}",
            )

        elif intermediate_steps[-1][0].tool == "get_dependency_graph":
            # If the prior step was to get the list of dependencies, then we need to create stubs for each of them
            code_dependency:CodeDependency = intermediate_steps[-1][1]

            dependency_names = self.get_unique_dependency_names(code_dependency)

            # Create a list of available stubs by iterating through each dependency, hacking off the file extension, and adding "stub" to the end, and then re-adding the file extension
            available_stubs = []
            for dependency in dependency_names:
                if dependency != "" and dependency != code_dependency.name:
                    dependency_split = dependency.split(".")
                    dependency_split[-2] = dependency_split[-2] + "Stub"
                    available_stubs.append(
                        f"For {dependency} use: {'.'.join(dependency_split)}"
                    )

            # Find the file_id for each dependency
            actions = []
            for dependency in dependency_names:
                if dependency != "" and dependency != code_dependency.name:
                    file = self.get_file_by_name(dependency, kwargs["collection_id"])
                    actions.append(
                        AgentAction(
                            tool="create_stub_code",
                            tool_input={
                                "file_id": file.id,
                                "available_dependencies": available_stubs,
                            },
                            log=f"Creating stubs for: {file.file_name}",
                        )
                    )

            return actions

        else:            
            final_result = '\n\n'.join([result[1]['code'] for result in intermediate_steps[1:]])

            return AgentFinish(
                {"output": final_result}, log="Finished stubbing"
            )
        
    def get_unique_dependency_names(self, code_dependency: CodeDependency):
        unique_names = set()
        
        def traverse_dependency(dependency:CodeDependency):
            unique_names.add(dependency.name)
            for sub_dependency in dependency.dependencies:
                traverse_dependency(sub_dependency)
        
        traverse_dependency(code_dependency)
        return list(unique_names)

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

    def get_file_by_name(self, file_name: str, collection_id: int):
        documents = Documents()
        return documents.get_file_by_name(file_name, collection_id)


# Testing
if __name__ == "__main__":
    agent = StubbingAgent()

    tools = []

    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent, tools=tools, verbose=True
    )

    agent_executor.run(file_id=11, collection_id=3)

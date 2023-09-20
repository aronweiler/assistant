import sys
import os
import json
from typing import Any, List, Tuple, Union


from langchain.agents import Tool, AgentExecutor, BaseMultiActionAgent
from langchain.schema import AgentAction, AgentFinish
from langchain.tools import StructuredTool
from langchain.base_language import BaseLanguageModel

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)

from src.ai.llm_helper import get_prompt

from src.db.models.software_development.user_needs import UserNeeds, UserNeedsModel
from src.db.models.software_development.requirements import (
    Requirements,
    RequirementsModel,
)
from src.db.models.software_development.design_decisions import (
    DesignDecisions,
    DesignDecisionsModel,
)

from src.db.models.documents import Documents
from src.db.models.domain.file_model import FileModel


class SystemArchitecture:
    def __init__(
        self,
        callbacks,
        llm_type: str,
        llm: BaseLanguageModel,
    ) -> None:
        self.agent = SystemArchitectureAgent()
        self.callbacks = callbacks
        self.llm_type = llm_type
        self.llm = llm

        tools = [
            StructuredTool.from_function(func=self.architectural_component_decomposition),
            StructuredTool.from_function(func=self.key_system_interfaces),
            StructuredTool.from_function(func=self.create_design_decisions),
        ]

        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent, tools=tools, verbose=True, callbacks=self.callbacks
        )

    def run(self, project, user_needs, requirements, design_decisions):
        return self.agent_executor.run(
            project=project,
            user_needs=user_needs,
            requirements=requirements,
            design_decisions=design_decisions,
            callbacks=self.callbacks
        )

    ## Create a bunch of tools to do the following:
    # Architectural component decomposition
    # Identification of key system interfaces
    # Make design decisions for each component
    # Definition of communication protocols and data flow (v2)
    # Overview of hardware and software infrastructure requirements  (v2)
    # Consideration of scalability and flexibility in the architecture  (v2)
    # Initial performance considerations and constraints  (v2)
    # Identification of potential risks or challenges related to the chosen architecture  (v2)
    # Alignment with any relevant industry or organizational standards  (v2)

    def architectural_component_decomposition(
        self, user_needs, requirements, design_decisions
    ):
        """Useful for describing the architectural components and their roles

        Args:
            user_needs: A list of user needs
            requirements: A list of requirements
            design_decisions: A list of exiting design decisions

        Returns:
            A detailed description of the architectural components and their roles
        """

        prompt = get_prompt(self.llm_type, "COMPONENT_DECOMPOSITION_TEMPLATE")

        prompt = prompt.format(
            user_needs="-" + "\n-".join([user_need.text for user_need in user_needs]),
            requirements="-"
            + "\n-".join([requirement.text for requirement in requirements]),
            # TODO: Make additional inputs smart- if it's code, use the code structure here.  If it's a document, possibly search and embed the document text here.
            # additional_inputs=[additional_input.description for additional_input in additional_inputs],
            existing_design_decisions="\n".join(
                [
                    f"- {design_decision.component} - {design_decision.decision}"
                    for design_decision in design_decisions
                ]
            ),
        )

        return self.llm.predict(prompt)

    def key_system_interfaces(self, components):
        """Useful for identifying key system interfaces

        Args:
            components_json: A JSON representation of the system components

        Returns:
            A list of key system interfaces
        """

        prompt = get_prompt(self.llm_type, "KEY_SYSTEM_INTERFACES_TEMPLATE")

        prompt = prompt.format(
            components=components,
        )

        return self.llm.predict(prompt)

    def create_design_decisions(
        self, project, requirements, components, interfaces, existing_design_decisions
    ):
        """Useful for creating design decisions

        Args:
            requirements: A list of requirements
            components: A list of components
            interfaces: A list of interfaces associated with the components
            existing_design_decisions: A list of exiting design decisions

        Returns:
            A list of design decisions
        """

        prompt = get_prompt(self.llm_type, "DESIGN_DECISION_TEMPLATE")

        # Get the components ordered by dependencies
        components_ordered = self.get_all_components_ordered(components)

        designs = []
        # Iterate through the components, and do the design
        for component in components_ordered:
            # Get the interfaces for this component
            related_interfaces = self.get_interfaces_by_component_name(
                interfaces, component["name"]
            )

            single_prompt = prompt.format(
                requirements="- "
                + "\n- ".join([requirement.text for requirement in requirements]),
                component=component,
                existing_design_decisions="\n".join(
                    [
                        f"- {design_decision.component} - {design_decision.decision} ({design_decision.details}))"
                        for design_decision in existing_design_decisions
                    ]
                ),
                interfaces=related_interfaces,
            )

            design_json = json.loads(self.llm.predict(single_prompt))

            for decision in design_json["Component Designs"]:
                # Append it to the existing designs so it feeds forward into the next design
                design = DesignDecisionsModel(
                    id=None, project_id=project.id, **decision
                )

                existing_design_decisions.append(design)
                # TODO: Stop dumping to json for production- this is just here for pretty output and testing
                designs.append(json.dumps(design.__dict__))

        return designs

    def get_all_components_ordered(self, components_data):
        sorted_components = []
        visited = set()

        def dfs(component):
            if component["name"] not in visited:
                visited.add(component["name"])
                dependencies = component.get("dependencies", [])
                for dependency in dependencies:
                    matching_dependency = next(
                        (
                            c
                            for c in components_data["Components"]
                            if c["name"] == dependency["dependency_name"]
                        ),
                        None,
                    )
                    if matching_dependency:
                        dfs(matching_dependency)
                sorted_components.append(component)

        for component in components_data["Components"]:
            dfs(component)

        sorted_components.reverse()

        return sorted_components

    def get_components_by_name(self, components_data, target_name):
        matching_components = [
            component
            for component in components_data
            if component["name"] == target_name
        ]
        return matching_components

    def get_interfaces_by_component_name(self, json_data, component_name):
        matching_interfaces = []

        # Iterate through the interfaces
        for interface in json_data["Interfaces"]:
            if interface["component_name"] == component_name:
                matching_interfaces.append(interface)

        return matching_interfaces


class SystemArchitectureAgent(BaseMultiActionAgent):
    """An agent that takes or performs the following steps in an effort to define a system architecture:

    Description of architectural components and their roles
    Identification of key system interfaces
    Definition of communication protocols and data flow
    Overview of hardware and software infrastructure requirements
    Consideration of scalability and flexibility in the architecture
    Initial performance considerations and constraints
    Identification of potential risks or challenges related to the chosen architecture
    Alignment with any relevant industry or organizational standards
    """

    @property
    def input_keys(self):
        # Note: These are just a few of the inputs that feed the system architecture stage of software development.
        # There are many more inputs that are not listed here, but these are what I am using for the purpose of prototype development.

        return ["project", "user_needs", "requirements", "design_decisions"]

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
            # First time into the agent, perform the architectural decomposition
            return AgentAction(
                tool="architectural_component_decomposition",
                tool_input={
                    "user_needs": kwargs["user_needs"],
                    "requirements": kwargs["requirements"],
                    "design_decisions": kwargs["design_decisions"],
                },
                log="Describing the architectural components and roles...\n",
            )
        elif intermediate_steps[-1][0].tool == "architectural_component_decomposition":
            # Now that we have the architectural decomposition, we can identify the key system interfaces
            components_json = intermediate_steps[-1][1]
            return AgentAction(
                tool="key_system_interfaces",
                tool_input={"components": components_json},
                log="Identifying key system interfaces...\n",
            )
        elif intermediate_steps[-1][0].tool == "key_system_interfaces":
            # Now that we have the architectural decomposition, we can identify the key system interfaces
            interfaces = json.loads(intermediate_steps[-1][1])
            components = json.loads(intermediate_steps[-2][1])

            return AgentAction(
                tool="create_design_decisions",
                # inputs are: requirements, components, interfaces, existing_design_decisions
                tool_input={
                    "project": kwargs["project"],
                    "requirements": kwargs["requirements"],
                    "components": components,
                    "interfaces": interfaces,
                    "existing_design_decisions": kwargs["design_decisions"],
                },
                log="Making design decisions...\n",
            )

        else:
            # Done handling steps, return the output
            output = []

            for step in intermediate_steps:
                output.append(step[1])

            return AgentFinish(
                {"output": output}, log="Finished the system architecture."
            )

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


# Testing
if __name__ == "__main__":
    components = """{
        "Components": [
                {
                        "name": "User Interface",
                        "purpose": "Provides a graphical interface for the user to interact with the tic-tac-toe game",
                        "inputs": [
                                "User input from mouse clicks",
                                "User input from keyboard (e.g., entering names, selecting marks)"
                        ],
                        "outputs": [
                                "Displaying the game board",
                                "Displaying game status messages",
                                "Displaying alerts to the user"
                        ],
                        "interactions": [
                                {
                                        "interacts_with": "Game Logic",
                                        "description": "Receives game state updates and displays the game board and messages accordingly"
                                },
                                {
                                        "interacts_with": "Alert System",
                                        "description": "Displays alerts to the user via pop-up windows"
                                }
                        ],
                        "data_handling": [
                                {
                                        "data_name": "User input",
                                        "data_type": "String",
                                        "description": "Handles user input for entering names, selecting marks, and making moves"
                                },
                                {
                                        "data_name": "Game state",
                                        "data_type": "Array",
                                        "description": "Receives and displays the current state of the game board"
                                },
                                {
                                        "data_name": "Game status",
                                        "data_type": "String",
                                        "description": "Displays messages indicating the game status (e.g., winner, draw)"
                                }
                        ],
                        "dependencies": [
                                {
                                        "dependency_name": "Game Logic",
                                        "description": "Relies on game state updates from the Game Logic component"
                                },
                                {
                                        "dependency_name": "Alert System",
                                        "description": "Relies on the Alert System to display alerts to the user"
                                }
                        ]
                },
                {
                        "name": "Game Logic",
                        "purpose": "Handles the game logic and rules of tic-tac-toe",
                        "inputs": [
                                "User input from User Interface (e.g., mouse clicks, keyboard input)"
                        ],
                        "outputs": [
                                "Updates game state",
                                "Updates game status"
                        ],
                        "interactions": [
                                {
                                        "interacts_with": "User Interface",
                                        "description": "Receives user input and updates the game state and status accordingly"
                                },
                                {
                                        "interacts_with": "Alert System",
                                        "description": "Sends alerts to the Alert System when a game is won, lost, or tied"
                                }
                        ],
                        "data_handling": [
                                {
                                        "data_name": "Game state",
                                        "data_type": "Array",
                                        "description": "Stores and updates the current state of the game board"
                                },
                                {
                                        "data_name": "Game status",
                                        "data_type": "String",
                                        "description": "Stores and updates the game status (e.g., winner, draw)"
                                }
                        ],
                        "dependencies": [
                                {
                                        "dependency_name": "User Interface",
                                        "description": "Relies on user input from the User Interface component"
                                },
                                {
                                        "dependency_name": "Alert System",
                                        "description": "Relies on the Alert System to send alerts"
                                }
                        ]
                },
                {
                        "name": "Alert System",
                        "purpose": "Handles displaying alerts to the user via pop-up windows",
                        "inputs": [
                                "Alert messages from User Interface",
                                "Game state updates from Game Logic"
                        ],
                        "outputs": [
                                "Displaying alerts to the user via pop-up windows"
                        ],
                        "interactions": [
                                {
                                        "interacts_with": "User Interface",
                                        "description": "Receives alert messages from the User Interface component"
                                },
                                {
                                        "interacts_with": "Game Logic",
                                        "description": "Receives game state updates from the Game Logic component"
                                }
                        ],
                        "data_handling": [
                                {
                                        "data_name": "Alert messages",
                                        "data_type": "String",
                                        "description": "Stores and displays alert messages to the user"
                                },
                                {
                                        "data_name": "Game state",
                                        "data_type": "Array",
                                        "description": "Receives and displays the current state of the game board"
                                }
                        ],
                        "dependencies": [
                                {
                                        "dependency_name": "User Interface",
                                        "description": "Relies on alert messages from the User Interface component"
                                },
                                {
                                        "dependency_name": "Game Logic",
                                        "description": "Relies on game state updates from the Game Logic component"
                                }
                        ]
                }
        ]
}"""

    interfaces = """{
        "Interfaces": [
                {
                        "name": "User Interface",
                        "component_name": "User Interface",
                        "purpose": "Provides a graphical interface for the user to interact with the tic-tac-toe game",
                        "inputs": [
                                {
                                        "input_type": "User input from mouse clicks",
                                        "description": "User input from mouse clicks on the game board"
                                },
                                {
                                        "input_type": "User input from keyboard",
                                        "description": "User input from keyboard for entering names, selecting marks, and making moves"
                                }
                        ],
                        "outputs": [
                                {
                                        "output_type": "Displaying the game board",
                                        "description": "Displays the current state of the game board"
                                },
                                {
                                        "output_type": "Displaying game status messages",
                                        "description": "Displays messages indicating the game status (e.g., winner, draw)"
                                },
                                {
                                        "output_type": "Displaying alerts to the user",
                                        "description": "Displays alerts to the user via pop-up windows"
                                }
                        ]
                },
                {
                        "name": "Game Logic",
                        "component_name": "Game Logic",
                        "purpose": "Handles the game logic and rules of tic-tac-toe",
                        "inputs": [
                                {
                                        "input_type": "User input from User Interface",
                                        "description": "Receives user input from the User Interface component"
                                }
                        ],
                        "outputs": [
                                {
                                        "output_type": "Updates game state",
                                        "description": "Updates the current state of the game board"
                                },
                                {
                                        "output_type": "Updates game status",
                                        "description": "Updates the game status (e.g., winner, draw)"
                                }
                        ]
                },
                {
                        "name": "Alert System",
                        "component_name": "Alert System",
                        "purpose": "Handles displaying alerts to the user via pop-up windows",
                        "inputs": [
                                {
                                        "input_type": "Alert messages from User Interface",
                                        "description": "Receives alert messages from the User Interface component"
                                },
                                {
                                        "input_type": "Game state updates from Game Logic",
                                        "description": "Receives game state updates from the Game Logic component"
                                }
                        ],
                        "outputs": [
                                {
                                        "output_type": "Displaying alerts to the user via pop-up windows",
                                        "description": "Displays alert messages to the user via pop-up windows"
                                }
                        ]
                }
        ]
}"""

    components_json = json.loads(components)
    interfaces_json = json.loads(interfaces)

    system_architecture = SystemArchitecture(None, None, None)

    print(system_architecture.get_all_components_ordered(components_json))
    print(
        system_architecture.get_interfaces_by_component_name(
            interfaces_json, "User Interface"
        )
    )

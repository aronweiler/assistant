import logging
import json
from uuid import UUID
from typing import List

from langchain.base_language import BaseLanguageModel
from langchain.prompts import PromptTemplate
from langchain.chains.router.llm_router import LLMRouterChain, RouterOutputParser
from langchain.memory.readonly import ReadOnlySharedMemory

from src.configuration.assistant_configuration import DesignDecisionGenerator as DesignDecisionGeneratorConfiguration

from src.ai.abstract_ai import AbstractAI
from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm
from src.ai.system_info import get_system_information
from src.ai.destinations.destination_base import DestinationBase
from src.ai.destination_route import DestinationRoute
from src.ai.callbacks.token_management_callback import TokenManagementCallbackHandler

from src.db.models.software_development.projects import Projects
from src.db.models.software_development.user_needs import UserNeeds
from src.db.models.software_development.requirements import Requirements
from src.db.models.documents import Documents
from src.db.models.software_development.design_decisions import DesignDecisions
from src.db.models.software_development.additional_design_inputs import AdditionalDesignInputs

from src.utilities.instance_utility import create_instance_from_module_and_class

class SingleShotDesignDecisionGenerator:
    """A design decision generator"""

    llm: BaseLanguageModel = None
    configuration: DesignDecisionGeneratorConfiguration

    def __init__(
        self,
        configuration: DesignDecisionGeneratorConfiguration,
        streaming: bool = False,        
    ):
        """Creates a new SingleShotDesignDecisionGenerator instance."""

        self.model_configuration = configuration.model_configuration
        self.token_management_handler = TokenManagementCallbackHandler()
        self.streaming = streaming

        self.llm = get_llm(
            self.model_configuration,
            callbacks=[self.token_management_handler],
            tags=["design-decision-generator"],
            streaming=streaming,
        )


    def generate(
        self,
        project_id: int,        
        llm_callbacks: list = [],
        agent_callbacks: list = [],
        kwargs: dict = {},
    ):
        """Generates design decisions for the specified project ID"""

        # Set up the helpers
        projects_helper = Projects()
        design_decisions_helper = DesignDecisions()
        user_needs_helper = UserNeeds()
        requirements_helper = Requirements()
        documents_helper = Documents()
        additional_inputs_helper = AdditionalDesignInputs()

        # Pull all of the project data from the database
        project = projects_helper.get_project(project_id)        
        user_needs = user_needs_helper.get_user_needs_in_project(project_id)
        requirements = requirements_helper.get_requirements_for_project(project_id)        
        
        # Create a design decision for each requirement        
        for requirement in requirements:
            # Get the design decisions (do this every time because we're adding new ones)
            design_decisions = design_decisions_helper.get_design_decisions_in_project(project_id)

            # Get any additional inputs for this requirement (TBD)
            additional_inputs = additional_inputs_helper.get_design_inputs_for_requirement(
                requirement.id
            )            

            prompt = get_prompt(
                self.model_configuration.llm_type,
                "SINGLE_SHOT_DESIGN_DECISION_TEMPLATE"
            )

            # Format the prompt
            prompt = prompt.format(
                project_name=project.project_name,
                user_needs="-" + "\n-".join([user_need.text for user_need in user_needs]),
                requirement_id=requirement.id,
                requirement=requirement.text,
                # TODO: Make additional inputs smart- if it's code, use the code structure here.  If it's a document, possibly search and embed the document text here.
                # additional_inputs=[additional_input.description for additional_input in additional_inputs],
                existing_design_decisions="\n".join([f"- {design_decision.category} - {design_decision.decision}" for design_decision in design_decisions]),
            )

            # Generate the design decision
            design_decision = self.llm.predict(prompt)
            print(design_decision)

            json_design_decisions = json.loads(design_decision)

            for decision in json_design_decisions['Components']:
                # Save the design decision to the database
                design_decisions_helper.create_design_decision(
                    project_id=project_id,
                    category=decision["name"],
                    decision=decision["decision"],
                    details=decision["details"],
                )   


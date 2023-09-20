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
from src.ai.llm_helper import get_llm, get_prompt
from src.ai.system_info import get_system_information
from src.ai.destinations.destination_base import DestinationBase
from src.ai.destination_route import DestinationRoute
from src.ai.callbacks.token_management_callback import TokenManagementCallbackHandler
from src.ai.agents.software_development.system_architecture import SystemArchitecture

from src.db.models.software_development.projects import Projects
from src.db.models.software_development.user_needs import UserNeeds
from src.db.models.software_development.requirements import Requirements
from src.db.models.documents import Documents
from src.db.models.software_development.design_decisions import DesignDecisions
from src.db.models.software_development.additional_design_inputs import AdditionalDesignInputs

from src.utilities.instance_utility import create_instance_from_module_and_class

class SystemArchitectureGenerator:
    """A system architecture generator"""

    llm: BaseLanguageModel = None
    configuration: DesignDecisionGeneratorConfiguration

    def __init__(
        self,
        configuration: DesignDecisionGeneratorConfiguration,
        streaming: bool = False,        
    ):
        self.model_configuration = configuration.model_configuration
        self.token_management_handler = TokenManagementCallbackHandler()
        self.streaming = streaming

        self.llm = get_llm(
            self.model_configuration,
            callbacks=[self.token_management_handler],
            tags=["system-architecture-generator"],
            streaming=streaming,
        )


    def generate(
        self,
        project_id: int,        
        llm_callbacks: list = [],
        agent_callbacks: list = [],
        kwargs: dict = {},
    ):
        """Generates architecture for the specified project ID"""

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
        design_decisions = design_decisions_helper.get_design_decisions_in_project(project_id)
        
        # Create the agent
        system_architecture = SystemArchitecture(agent_callbacks, self.model_configuration.llm_type, self.llm)

        result = system_architecture.run(project, user_needs, requirements, design_decisions)

        # TODO: Store the results in the database

        return result


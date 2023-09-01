import logging
from uuid import UUID
from typing import List

from langchain.base_language import BaseLanguageModel
from langchain.prompts import PromptTemplate
from langchain.chains.router.llm_router import LLMRouterChain, RouterOutputParser

from configuration.assistant_configuration import AssistantConfiguration, Destination

from ai.abstract_ai import AbstractAI
from ai.prompts import MULTI_PROMPT_ROUTER_TEMPLATE, SUMMARIZE_FOR_LABEL_TEMPLATE
from ai.interactions.interaction_manager import InteractionManager
from ai.llm_helper import get_llm
from ai.system_info import get_system_information
from ai.destinations.destination_base import DestinationBase
from ai.destination_route import DestinationRoute

from utilities.instance_utility import create_instance_from_module_and_class


class RequestRouter(AbstractAI):
    """A Router AI that examines the user's input and routes it to the appropriate AI (using an LLM to determine the AI to use)"""

    llm: BaseLanguageModel = None
    interaction_manager: InteractionManager
    assistant_configuration: AssistantConfiguration

    def __init__(
        self, assistant_configuration: AssistantConfiguration, interaction_id: UUID
    ):
        """Creates a new RequestRouter

        Args:
            ai_configuration (AIConfiguration): AI configuration
            interaction_id (UUID, optional): The interaction ID to use for this router.
            user_id (int): The user ID to use for this router.
        """
        self.assistant_configuration = assistant_configuration
        self.llm = get_llm(assistant_configuration.request_router.model_configuration)

        # Set up the interaction manager
        self.interaction_manager = InteractionManager(
            interaction_id,
            assistant_configuration.user_email,
            self.llm,
            assistant_configuration.db_env_location,
            assistant_configuration.request_router.model_configuration.max_conversation_history_tokens,
        )

        self._create_routes(assistant_configuration.request_router.destination_routes)

        self._create_router_chain()

    def query(self, query: str, collection_id: int = None):
        """Routes the query to the appropriate AI, and returns the response."""

        # Set the document collection id on the interaction manager
        self.interaction_manager.collection_id = collection_id

        if self.interaction_manager.interaction_needs_summary:
            interaction_summary = self.llm.predict(
                SUMMARIZE_FOR_LABEL_TEMPLATE.format(query=query)
            )
            self.interaction_manager.set_interaction_summary(interaction_summary)
            self.interaction_manager.interaction_needs_summary = False

        # Execute the router chain
        router_result = self.router_chain(
            {
                "input": query,
                "chat_history": "\n".join(
                    [
                        f"{'AI' if m.type == 'ai' else f'{self.interaction_manager.user_name} ({self.interaction_manager.user_email})'}: {m.content}"
                        for m in self.interaction_manager.postgres_chat_message_history.messages[
                            -8:
                        ]
                    ]
                ),
                "system_information": get_system_information(
                    self.interaction_manager.user_location
                ),
                "loaded_documents": "\n".join(
                    self.interaction_manager.get_loaded_documents()
                ),
            }
        )

        return self._route_response(router_result, query)

    def _route_response(self, router_result, query):
        """Routes the response from the router chain to the appropriate AI, and returns the response."""

        if "destination" in router_result and router_result["destination"] is not None:
            # Get the destination chain
            destination = next(
                (c for c in self.routes if c.name == router_result["destination"]),
                None,
            )

            if destination is not None:
                logging.debug(f"Routing to destination: {destination.name}")

                response = destination.instance.run(input=query) # router_result['next_inputs']['input']) # Use the original query for now

                logging.debug(f"Response from LLM: {response}")
        
                return response
            

        logging.error(
            f"Destination not specified by the router chain. Cannot route response. Router response was: {router_result}.\n\nGetting default chain."
        )

        # If we got here, something went wrong.  Get the default chain.
        destination = next(
            (c for c in self.routes if c.is_default == True),
            None,
        )
        
        destination.instance.run(input=query)
        

    def _create_router_chain(self):
        """Creates the router chain for this router."""

        destinations = [f"{r.name}: {r.description}" for r in self.routes]

        destinations_str = "\n".join(destinations)

        router_template = MULTI_PROMPT_ROUTER_TEMPLATE.format(
            destinations=destinations_str
        )

        router_prompt = PromptTemplate(
            template=router_template,
            input_variables=[
                "input",
                "chat_history",
                "system_information",
                "loaded_documents",
            ],
            output_parser=RouterOutputParser(),
        )

        self.router_chain = LLMRouterChain.from_llm(
            self.llm,
            router_prompt,
            input_keys=[
                "input",
                "chat_history",
                "system_information",
                "loaded_documents",
            ],
        )

    def _create_routes(self, destination_routes):
        """Creates the routes for the specified destination routes."""

        self.routes: List[DestinationRoute] = []

        for destination in destination_routes:
            destination = self._create_destination(destination)
            self.routes.append(destination)

    def _create_destination(self, destination: Destination):
        """Creates an instance of a DestinationBase from the specified destination."""
        instance: DestinationBase = create_instance_from_module_and_class(
            module_name=destination.module,
            class_name=destination.class_name,
            constructor_kwargs={
                "destination": destination,
                "interaction_manager": self.interaction_manager,
            },
        )

        return DestinationRoute(
            name=destination.name,
            description=destination.description,
            is_default=destination.is_default,
            instance=instance,
        )

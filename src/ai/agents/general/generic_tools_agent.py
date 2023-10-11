import re
import json
from typing import Any, List, Tuple, Union
import logging

from langchain.schema import AgentAction
from langchain.schema.language_model import BaseLanguageModel
from langchain.agents import (
    AgentExecutor,
    BaseMultiActionAgent,
)
from langchain.schema import AgentAction, AgentFinish
from langchain.tools import StructuredTool
from langchain.base_language import BaseLanguageModel

from src.ai.llm_helper import get_prompt, get_llm
from src.ai.interactions.interaction_manager import InteractionManager
from src.configuration.assistant_configuration import ModelConfiguration


class GenericTool:
    def __init__(
        self, description, function, return_direct=False, additional_instructions=None
    ):
        self.description = description
        self.additional_instructions = additional_instructions
        self.function = function
        self.schema = self.extract_function_schema(function)
        self.name = self.schema["name"]
        self.structured_tool = StructuredTool.from_function(
            func=self.function, return_direct=return_direct
        )

    def extract_function_schema(self, func):
        import inspect

        sig = inspect.signature(func)
        parameters = []

        for param_name, param in sig.parameters.items():
            param_info = {
                "argument_name": param_name,
                "argument_type": str(param.annotation.__name__),
                "required": "optional"
                if param.default != inspect.Parameter.empty
                else "required",
            }
            parameters.append(param_info)

        schema = {"name": func.__name__, "parameters": parameters}

        return schema


class GenericToolsAgent(BaseMultiActionAgent):
    model_configuration: ModelConfiguration = None
    interaction_manager: InteractionManager = None
    tools: list = None
    previous_work: str = None
    llm: BaseLanguageModel = None
    callbacks: list = None
    streaming: bool = True
    step_plans: dict = None
    step_index: int = -1

    class Config:
        arbitrary_types_allowed = True  # Enable the use of arbitrary types

    @property
    def input_keys(self):
        return [
            "input",
            "system_information",
            "user_name",
            "user_email",
        ]

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

        # First time into the agent (agent.run)
        # Create the prompt with which to start the conversation (planning)
        if not intermediate_steps:
            self.llm = get_llm(
                model_configuration=self.model_configuration,
                tags=["generic_tools"],
                callbacks=kwargs["callbacks"],
                streaming=self.streaming,
            )

            plan_steps_prompt = self.get_plan_steps_prompt(
                user_query=kwargs["input"],
                system_information=kwargs["system_information"],
                user_name=kwargs["user_name"],
                user_email=kwargs["user_email"],
            )

            # Save the step plans for future reference
            self.step_plans = self.parse_json(self.llm.predict(plan_steps_prompt))
            # Make sure we're starting at the beginning
            self.step_index = 0

        # If we still have steps to perform
        if self.step_index < len(self.step_plans["steps"]):
            # This is a multi-action agent, but we're going to use it sequentially for now
            # TODO: Refactor this so we can execute multiple actions at once (and handle dependencies)

            # Create the first tool use prompt
            tool_use_prompt = self.get_tool_use_prompt(
                step=self.step_plans["steps"][self.step_index],
                helpful_context=self.get_helpful_context(intermediate_steps),
                user_query=kwargs["input"],
            )

            action_json = self.parse_json(self.llm.predict(tool_use_prompt))

            action = AgentAction(
                tool=action_json["tool"],
                tool_input=action_json["tool_args"]
                if "tool_args" in action_json
                else {},
                log=action_json["tool_use_description"],
            )

            self.step_index += 1

            return action

        # If we're done with the steps, return the final answer
        else:
            # Construct a prompt that will return the final answer based on all of the previously returned steps/context
            answer_prompt = self.get_answer_prompt(
                user_query=kwargs["input"],
                helpful_context=self.get_helpful_context(intermediate_steps),
            )

            answer_response = self.llm.predict(answer_prompt)

            return AgentFinish(
                return_values={"output": answer_response},
                log="Agent finished.",
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

    def parse_json(self, text: str) -> dict:
        pattern = re.compile(r"```(?:json)?\n(.*?)```", re.DOTALL)
        try:
            action_match = pattern.search(text)
            if action_match is not None:
                response = json.loads(action_match.group(1).strip(), strict=False)
                return response
            elif text.startswith("{") and text.endswith("}"):
                return json.loads(text.strip(), strict=False)
            else:
                # Just return this as the answer??
                return {"answer": text}
        except Exception as e:
            raise Exception(f"Could not parse LLM output: {text}") from e

    def get_helpful_context(self, intermediate_steps):
        if not intermediate_steps or len(intermediate_steps) == 0:
            return "No helpful context, sorry!"

        return "\n----\n".join([s[1] for s in intermediate_steps if s[1] not None])

    def get_plan_steps_prompt(
        self, user_query, system_information, user_name, user_email
    ):
        system_prompt = self.get_system_prompt(
            "Detail oriented, organized, and logical.", system_information
        )
        available_tools = self.get_available_tool_descriptions(self.tools)
        loaded_documents = self.get_loaded_documents()
        chat_history = self.get_chat_history()

        agent_prompt = get_prompt(
            self.model_configuration.llm_type,
            "PLAN_STEPS_NO_TOOL_USE_TEMPLATE",
        ).format(
            system_prompt=system_prompt,
            available_tool_descriptions=available_tools,
            loaded_documents=loaded_documents,
            chat_history=chat_history,
            user_query=f"{user_name} ({user_email}): {user_query}",
        )

        return agent_prompt

    def get_answer_prompt(self, user_query, helpful_context):
        agent_prompt = get_prompt(
            self.model_configuration.llm_type,
            "ANSWER_PROMPT_TEMPLATE",
        ).format(user_query=user_query, helpful_context=helpful_context)

        return agent_prompt

    def get_tool_use_prompt(self, step, helpful_context, user_query):
        tool_name = step["tool"]
        tool_details = ""
        for tool in self.tools:
            if tool.name == tool_name:
                tool_details = self.get_tool_string(tool=tool)

        agent_prompt = get_prompt(
            self.model_configuration.llm_type,
            "TOOL_USE_TEMPLATE",
        ).format(
            loaded_documents=self.get_loaded_documents(),
            helpful_context=helpful_context,
            tool_name=tool_name,
            tool_details=tool_details,
            tool_use_description=step["step_description"],
            user_query=user_query,
        )

        return agent_prompt

    def get_system_prompt(self, personality_descriptors, system_information):
        system_prompt = get_prompt(
            self.model_configuration.llm_type,
            "SYSTEM_TEMPLATE",
        ).format(
            personality_descriptors=personality_descriptors,
            system_information=system_information,
        )

        return system_prompt

    def get_tool_string(self, tool):
        args_schema = "\n\t".join(
            [
                f"{t['argument_name']}, {t['argument_type']}, {t['required']}"
                for t in tool.schema["parameters"]
            ]
        )
        if tool.additional_instructions:
            additional_instructions = (
                "\nAdditional Instructions: " + tool.additional_instructions
            )
        else:
            additional_instructions = ""

        return f"Name: {tool.name}\nDescription: {tool.description}{additional_instructions}\nArgs (name, type, optional/required):\n\t{args_schema}"

    def get_available_tool_descriptions(self, tools: list[GenericTool]):
        tool_strings = []
        for tool in tools:
            if tool.additional_instructions:
                additional_instructions = (
                    "\nAdditional Instructions: " + tool.additional_instructions
                )
            else:
                additional_instructions = ""

            tool_strings.append(
                f"Name: {tool.name}\nDescription: {tool.description}{additional_instructions}"
            )

        formatted_tools = "\n----\n".join(tool_strings)

        return formatted_tools

    def get_loaded_documents(self):
        if self.interaction_manager:
            return "\n".join(
                self.interaction_manager.get_loaded_documents_for_reference()
            )
        else:
            return "No documents loaded."

    def get_chat_history(self):
        if self.interaction_manager:
            return (
                self.interaction_manager.conversation_token_buffer_memory.buffer_as_str
            )
        else:
            return "No chat history."

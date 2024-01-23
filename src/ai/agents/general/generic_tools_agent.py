import re
import json
from typing import Any, List, Optional, Tuple, Union
import logging

from langchain.schema import AgentAction
from langchain.schema.language_model import BaseLanguageModel
from langchain.agents import AgentExecutor, BaseMultiActionAgent, BaseSingleActionAgent
from langchain.schema import AgentAction, AgentFinish
from langchain.tools import StructuredTool
from langchain.base_language import BaseLanguageModel

from langchain_core.callbacks.base import BaseCallbackHandler, BaseCallbackManager

from src.ai.agents.general.generic_tool import GenericTool
from src.ai.agents.general.generic_tool_agent_helpers import GenericToolAgentHelpers

from src.ai.llm_helper import get_llm
from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.tools.tool_manager import ToolManager
from src.configuration.assistant_configuration import ModelConfiguration
from src.utilities.configuration_utilities import get_app_configuration

from src.utilities.parsing_utilities import parse_json


class GenericToolsAgent(BaseSingleActionAgent):
    model_configuration: ModelConfiguration
    conversation_manager: ConversationManager
    tool_manager: ToolManager
    tools: List[GenericTool]
    streaming: bool = True
    previous_work: str = ""
    llm: BaseLanguageModel = None
    generic_tools_agent_helpers: GenericToolAgentHelpers = None
    step_plans: dict = None
    step_index: int = -1
    current_retries: int = 0
    wrong_tool_calls: list = []

    class Config:
        arbitrary_types_allowed = True  # Enable the use of arbitrary types

    def __init__(
        self,
        model_configuration: ModelConfiguration,
        conversation_manager: ConversationManager,
        tool_manager: ToolManager,
        tools: List[GenericTool],
        streaming: bool = True,
    ):
        """Initialize the agent.

        Args:
            model_configuration: Configuration for the agent.
            conversation_manager: Conversation manager.
            tools: List of tools to use.
            previous_work: Previous work to use.
            streaming: Whether or not to stream the output.
        """
        super().__init__(
            model_configuration=model_configuration,
            conversation_manager=conversation_manager,
            tool_manager=tool_manager,
            tools=tools,
            streaming=streaming,
        )

        self.model_configuration = model_configuration
        self.conversation_manager = conversation_manager
        self.tool_manager = tool_manager
        self.tools = tools
        self.streaming = streaming

        self.generic_tools_agent_helpers = GenericToolAgentHelpers(
            conversation_manager=self.conversation_manager
        )

        self.llm = get_llm(
            model_configuration=self.model_configuration,
            tags=["generic_tools"],
            callbacks=self.conversation_manager.agent_callbacks,
            streaming=self.streaming,
        )

        self.previous_work = ""
        self.step_plans = None
        self.step_index = -1
        self.current_retries = 0
        self.wrong_tool_calls = []

    @property
    def input_keys(self):
        return [
            "input",
            "system_information",
            "user_name",
            "user_email",
        ]

    def plan(
        self,
        intermediate_steps: Tuple[AgentAction, str],
        callbacks: Optional[
            Union[List[BaseCallbackHandler], BaseCallbackManager]
        ] = None,
        **kwargs: Any,
    ) -> Union[AgentAction, AgentFinish]:
        """Given input, decided what to do.

        Args:
            intermediate_steps: Steps the LLM has taken to date,
                along with observations
            **kwargs: User inputs.

        Returns:
            Action specifying what tool to use.
        """

        # First time into the agent (agent.run)
        # Create the prompt with which to start the conversation (planning), which should generate steps (or a direct answer)
        if not intermediate_steps:
            self.get_step_plans_or_direct_answer(kwargs)

            if "answer" in self.step_plans or "final_answer" in self.step_plans:
                return AgentFinish(
                    return_values={
                        "output": self.step_plans["answer"]
                        if "answer" in self.step_plans
                        else self.step_plans["final_answer"]
                    },
                    log="Agent finished, answering directly.",
                )
                
        else:
            # This is where I should put the code to have the LLM evaluate the last intermediate step, and either re-plan or continue
            if 
            pass

        # If there are intermediate steps and we've called a tool, save the tool call results for the last step
        if len(intermediate_steps) > 0 and intermediate_steps[-1][0].tool is not None:
            self.conversation_manager.conversations_helper.add_tool_call_results(
                conversation_id=self.conversation_manager.conversation_id,
                tool_name=intermediate_steps[-1][0].tool,
                tool_arguments=json.dumps(intermediate_steps[-1][0].tool_input),
                tool_results=intermediate_steps[-1][1],
                include_in_conversation=self.tool_manager.should_include_in_conversation(
                    intermediate_steps[-1][0].tool
                ),
            )

        # If we don't have any steps, we're done
        if "steps" not in self.step_plans:
            return AgentFinish(
                return_values={
                    "output": "The previous AI could not properly generate any steps- here the raw value it returned:\n"
                    + self.step_plans
                },
                log="Agent finished, no steps found.",
            )

        # If we're here, we have steps to perform
        # Filter out any of the steps that use tools we don't have (because the AI hallucinates).
        self.step_plans["steps"] = self.remove_steps_without_tool(
            self.step_plans["steps"], self.tools
        )

        # If we still have steps to perform, after removing the ones we don't have tools for, perform them
        if (
            self.step_index < len(self.step_plans["steps"])
            and len(self.step_plans["steps"]) > 0
        ):
            # TODO: Refactor this so we can execute multiple actions at once (and handle dependencies)

            action = self.prompt_and_predict_tool_use(intermediate_steps, **kwargs)

            self.step_index += 1

            return action

        # If we're done with the steps, return the final answer
        else:
            # Construct a prompt that will return the final answer based on all of the previously returned steps/context
            answer_prompt = self.generic_tools_agent_helpers.get_answer_prompt(
                user_query=kwargs["input"],
                helpful_context=self.get_helpful_context(intermediate_steps),
            )

            answer_response = self.llm.invoke(
                answer_prompt,
                # callbacks=self.conversation_manager.agent_callbacks
            )

            answer = parse_json(text=answer_response.content, llm=self.llm)

            # If answer is a fail, we need to retry the last step with the added context from the tool failure
            if isinstance(answer, dict):
                if "answer" in answer or "final_answer" in answer:
                    answer_response = (
                        answer["answer"]
                        if "answer" in answer
                        else answer["final_answer"]
                    )
                else:
                    if self.current_retries >= self.model_configuration.max_retries:
                        return AgentFinish(
                            return_values={
                                "output": "I ran out of retries attempting to answer.  Here's my last output:\n"
                                + answer_response.content
                            },
                            log="Agent finished.",
                        )

                    self.current_retries += 1
                    self.step_index -= 1

                    # Reconstruct the tool use prompt with the new context to try to get around the failure
                    action = self.prompt_and_predict_tool_use_retry(
                        intermediate_steps, **kwargs
                    )
                    # action.log = f"Failed... retrying ({self.current_retries})"

                    logging.info(
                        f"Failed... retrying ({self.current_retries}): {answer_response}"
                    )

                    return action

            return AgentFinish(
                return_values={"output": answer_response},
                log="Agent finished.",
            )

    def get_step_plans_or_direct_answer(self, kwargs):
        plan_steps_prompt = self.get_plan_steps_prompt(
            user_query=kwargs["input"],
            system_information=kwargs["system_information"],
            user_name=kwargs["user_name"],
            user_email=kwargs["user_email"],
        )

        plan = self.llm.invoke(
            plan_steps_prompt,
            # callbacks=self.conversation_manager.agent_callbacks,
        )

        # Save the step plans for future reference
        self.step_plans = parse_json(
            plan.content,
            llm=self.llm,
        )
        # Make sure we're starting at the beginning
        self.step_index = 0

    def remove_steps_without_tool(self, steps, tools):
        # Create a set containing the names of tools for faster lookup
        tool_names = [tool.name for tool in tools]

        # Create a new list to store the filtered steps
        filtered_steps = []

        # Iterate over each step and check if its tool is in the set of tool names
        for step in steps:
            if "tool" not in step or step["tool"].strip() == "":
                logging.error(
                    f"Step does not have a tool: {step}.  Skipping this step."
                )
                self.wrong_tool_calls.append(step)

                continue

            if step["tool"] in tool_names:
                filtered_steps.append(step)
            else:
                self.wrong_tool_calls.append(step)

        return filtered_steps

    def prompt_and_predict_tool_use(
        self, intermediate_steps, **kwargs: Any
    ) -> AgentAction:
        # Create the first tool use prompt
        tool_use_prompt = self.get_tool_use_prompt(
            step=self.step_plans["steps"][self.step_index],
            helpful_context=self.get_helpful_context(intermediate_steps),
            user_query=kwargs["input"],
            system_information=kwargs["system_information"],
        )

        text = self.llm.invoke(
            tool_use_prompt,
            # callbacks=self.conversation_manager.agent_callbacks
        )

        action_json = parse_json(
            text.content,
            llm=self.llm,
        )

        if "final_answer" in action_json:
            return AgentFinish(
                return_values={"output": action_json["final_answer"]},
                log="Agent finished, answering directly.",
            )

        action = AgentAction(
            tool=action_json["tool"],
            tool_input=action_json["tool_args"] if "tool_args" in action_json else {},
            log=action_json["tool_use_description"]
            if "tool_use_description" in action_json
            else "Could not find tool_use_description in response.",
        )

        return action

    def prompt_and_predict_tool_use_retry(
        self, intermediate_steps, **kwargs: Any
    ) -> AgentAction:
        # Create the first tool use prompt
        if self.step_index == -1:
            # Handle the case where no steps could be found
            step = {
                "step_description": f"No valid steps could be found.  Here is the user's query, in case it helps: {kwargs['input']}.\n\nIn addition, here is ALL of the step data we could gather:\n{json.dumps(self.wrong_tool_calls, indent=4)}"
            }
        else:
            step = self.step_plans["steps"][self.step_index]

        tool_use_prompt = self.get_tool_use_retry_prompt(
            step=step,
            previous_tool_attempts=self.get_tool_calls_from_failed_steps(
                intermediate_steps
            ),
            user_query=kwargs["input"],
            system_information=kwargs["system_information"],
        )

        action_json = parse_json(
            text=self.llm.invoke(
                tool_use_prompt,
                # callbacks=self.conversation_manager.agent_callbacks
            ).content,
            llm=self.llm,
        )

        action = AgentAction(
            tool=action_json["tool"],
            tool_input=action_json["tool_args"] if "tool_args" in action_json else {},
            log=action_json["tool_use_description"],
        )

        return action

    def get_tool_calls_from_failed_steps(self, intermediate_steps):
        context = ""
        for step in intermediate_steps:
            context += json.dumps(
                {
                    "tool_use_description": intermediate_steps[-1][0].log,
                    "tool": intermediate_steps[-1][0].tool,
                    "tool_args": intermediate_steps[-1][0].tool_input,
                }
            )

            try:
                if step[1] is not None:
                    context += "\nReturned: " + str(step[1])
                else:
                    context += "\nReturned: None"
            except Exception as e:
                context += "\nReturned: An unknown exception."

        return context

    def get_helpful_context(self, intermediate_steps):
        if not intermediate_steps or len(intermediate_steps) == 0:
            return "No helpful context, sorry!"

        return "\n----\n".join(
            [
                f"using the `{s[0].tool}` tool returned:\n'{s[1]}'"
                for s in intermediate_steps
                if s[1] is not None
            ]
        )

    def get_plan_steps_prompt(
        self, user_query, system_information, user_name, user_email
    ):
        agent_prompt = self.conversation_manager.prompt_manager.get_prompt(
            "generic_tools_agent_prompts",
            "PLAN_STEPS_NO_TOOL_USE_TEMPLATE",
        ).format(
            system_prompt=self.generic_tools_agent_helpers.get_system_prompt(
                system_information
            ),
            available_tool_descriptions=self.generic_tools_agent_helpers.get_available_tool_descriptions(
                self.tools
            ),
            loaded_documents_prompt=self.generic_tools_agent_helpers.get_loaded_documents_prompt(),
            selected_repository_prompt=self.generic_tools_agent_helpers.get_selected_repo_prompt(),
            chat_history_prompt=self.generic_tools_agent_helpers.get_chat_history_prompt(),
            previous_tool_calls_prompt=self.generic_tools_agent_helpers.get_previous_tool_calls_prompt(),
            user_query=f"{user_name} ({user_email}): {user_query}",
        )

        return agent_prompt

    def get_tool_use_prompt(
        self, step, helpful_context, user_query, system_information
    ):
        tool_name = step["tool"]
        tool_details = ""
        for tool in self.tools:
            if tool.name == tool_name:
                tool_details = self._get_formatted_tool_string(tool=tool)

        if len(self.wrong_tool_calls) > 0:
            formatted_wrong_tool_calls = "\n".join(
                [f"{p}" for p in self.wrong_tool_calls]
            )
            helpful_context = f"The planning AI (which is supposed to plan out steps to accomplish the user's goal) came up with these invalid tool calls: {formatted_wrong_tool_calls}.\n\nPlease examine these imaginary (or incorrect) tool calls, and let them inform your tool use and eventual answer here."

            # Reset the wrong tool calls
            self.wrong_tool_calls = []

        agent_prompt = self.conversation_manager.prompt_manager.get_prompt(
            "generic_tools_agent_prompts",
            "TOOL_USE_TEMPLATE",
        ).format(
            selected_repository_prompt=self.generic_tools_agent_helpers.get_selected_repo_prompt(),
            loaded_documents_prompt=self.generic_tools_agent_helpers.get_loaded_documents_prompt(),
            previous_tool_calls_prompt=self.generic_tools_agent_helpers.get_previous_tool_calls_prompt(),
            helpful_context=helpful_context,
            tool_name=tool_name,
            tool_details=tool_details,
            tool_use_description=step["step_description"],
            user_query=user_query,
            chat_history_prompt=self.generic_tools_agent_helpers.get_chat_history_prompt(),
            system_prompt=self.generic_tools_agent_helpers.get_system_prompt(
                system_information,
            ),
        )

        return agent_prompt

    def get_tool_use_retry_prompt(
        self, step, previous_tool_attempts, user_query, system_information
    ):
        available_tools = (
            self.generic_tools_agent_helpers.get_available_tool_descriptions(self.tools)
        )

        agent_prompt = self.conversation_manager.prompt_manager.get_prompt(
            "generic_tools_agent_prompts",
            "TOOL_USE_RETRY_TEMPLATE",
        ).format(
            loaded_documents=self.generic_tools_agent_helpers.get_loaded_documents_prompt(),
            previous_tool_attempts=previous_tool_attempts,
            available_tool_descriptions=available_tools,
            tool_use_description=step["step_description"],
            user_query=user_query,
            chat_history=self.generic_tools_agent_helpers.get_chat_history(),
            system_prompt=self.generic_tools_agent_helpers.get_system_prompt(
                system_information
            ),
        )

        return agent_prompt

    def _get_formatted_tool_string(self, tool: GenericTool):
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

    async def aplan(
        self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any
    ) -> Union[List[AgentAction], AgentFinish]:
        raise NotImplementedError("Async plan not implemented.")

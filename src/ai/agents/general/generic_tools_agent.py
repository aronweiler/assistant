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

from src.ai.utilities.llm_helper import get_llm
from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.prompts.prompt_models.answer import AnswerInput, AnswerOutput
from src.ai.prompts.prompt_models.evaluation import EvaluationInput, EvaluationOutput
from src.ai.prompts.prompt_models.planning_stage import (
    PlanningStageInput,
    PlanningStageOutput,
)
from src.ai.prompts.prompt_models.tool_use import (
    ToolUseInput,
    ToolUseOutput,
    ToolUseRetryInput,
)
from src.ai.prompts.query_helper import QueryHelper
from src.ai.tools.tool_manager import ToolManager
from src.configuration.assistant_configuration import ModelConfiguration
from src.utilities.configuration_utilities import get_app_configuration

from src.utilities.parsing_utilities import parse_json


class GenericToolsAgent(BaseSingleActionAgent):
    model_configuration: ModelConfiguration
    conversation_manager: ConversationManager
    tool_manager: ToolManager
    tools: List[GenericTool]
    query_helper: QueryHelper = None
    streaming: bool = True
    previous_work: str = ""
    llm: BaseLanguageModel = None
    planning_results: PlanningStageOutput = None
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

        self.llm = get_llm(
            model_configuration=self.model_configuration,
            tags=["generic_tools"],
            streaming=self.streaming,
            callbacks=self.conversation_manager.agent_callbacks,
        )

        self.query_helper = QueryHelper(self.conversation_manager.prompt_manager)

        self.previous_work = ""
        self.planning_results = None
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
            "evaluate_response",
            "re_planning_threshold",
            "rephrase_answer_instructions",
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
            # Reset the step_index to make sure we're starting at the beginning
            self.step_index = 0

            self.planning_results = self.get_step_plans_or_direct_answer(kwargs)

            if self.planning_results.action == "answer":
                return AgentFinish(
                    return_values={"output": self.planning_results.answer},
                    log="Agent finished, answering directly.",
                )

        else:
            # This is where I should put the code to have the LLM evaluate the last intermediate step, and either re-plan or continue
            pass

        # If there are intermediate steps and we've called a tool, save the tool call results for the last step
        if len(intermediate_steps) > 0 and intermediate_steps[-1][0].tool is not None:
            tool_results = intermediate_steps[-1][1]
            # if the tool results are a dictionary or a string, leave them.  If it's a pydantic model, convert it to a dictionary.
            if hasattr(tool_results, "dict"):
                tool_results = tool_results.dict()

            self.conversation_manager.conversations_helper.add_tool_call_results(
                conversation_id=self.conversation_manager.conversation_id,
                tool_name=intermediate_steps[-1][0].tool,
                tool_arguments=json.dumps(intermediate_steps[-1][0].tool_input),
                tool_results=tool_results,
                include_in_conversation=ToolManager.should_include_in_conversation(
                    tool_name=intermediate_steps[-1][0].tool,
                    conversation_manager=self.conversation_manager,
                ),
            )

        # If the AI didn't give us steps, return whatever it was that it gave us
        if self.planning_results.action != "execute_steps":
            return AgentFinish(
                return_values={
                    "output": "The previous AI could not properly generate any steps- here the raw value it returned:\n"
                    + self.planning_results
                },
                log="Agent finished, no steps found.",
            )

        # If we're here, we have steps to perform
        # Filter out any of the steps that use tools we don't have (because the AI hallucinates).
        self.planning_results.steps = self.remove_steps_without_tool(
            self.planning_results.steps, self.tools
        )

        # If we still have steps to perform, after removing the ones we don't have tools for, perform them
        if (
            self.step_index < len(self.planning_results.steps)
            and len(self.planning_results.steps) > 0
        ):
            # TODO: Refactor this so we can execute multiple actions at once (and handle dependencies)

            action = self.prompt_and_predict_tool_use(intermediate_steps, **kwargs)

            self.step_index += 1

            return action

        # If we're done with the steps, return the final answer
        else:
            input_object = AnswerInput(
                user_query=kwargs["input"],
                helpful_context=self.get_helpful_context(intermediate_steps),
                chat_history=self.conversation_manager.get_chat_history_prompt(),
                rephrase_answer_instructions_prompt=self.get_rephrase_prompt(kwargs),
            )

            result: AnswerOutput = self.query_helper.query_llm(
                llm=self.llm,
                input_class_instance=input_object,
                prompt_template_name="ANSWER_PROMPT_TEMPLATE",
                output_class_type=AnswerOutput,
                metadata={"output_type": "AnswerOutput"},
            )

            # Check to see if the result is a failure or not
            if result.status != "failure":
                answer_response = result.answer
            else:
                # If the answer was a failure, check the retries before we continue
                if self.current_retries >= self.model_configuration.max_retries:
                    return AgentFinish(
                        return_values={
                            "output": "I ran out of retries attempting to answer.  Here's my last output:\n"
                            + result.answer
                        },
                        log="Agent finished.",
                    )

                # If we still have retries, try again- increment the retries and decrement the step index to go back one step
                self.current_retries += 1
                self.step_index -= 1

                # Reconstruct the tool use prompt with the new context to try to get around the failure
                action = self.prompt_and_predict_tool_use_retry(
                    intermediate_steps, **kwargs
                )
                # action.log = f"Failed... retrying ({self.current_retries})"

                logging.info(f"Failed... retrying ({self.current_retries}): {result}")

                return action

            if kwargs["evaluate_response"]:
                # TODO: Finish this implementation
                try:
                    evaluation = self.evaluate_response(
                        answer_response, intermediate_steps, **kwargs
                    )

                    if kwargs.get("re_planning_threshold", 0.5) >= evaluation.score:
                        # Re-enter the planning stage
                        logging.error(
                            f"TODO- IMPLEMENT THIS:: Re-entering planning stage, because the evaluation score was too low: {evaluation.score}"
                        )
                except Exception as e:
                    logging.error(f"Evaluation failed, {e}")

            return AgentFinish(
                return_values={"output": answer_response},
                log="Agent finished.",
            )

    def evaluate_response(
        self, response, intermediate_steps, **kwargs
    ) -> EvaluationOutput:
        input_object = EvaluationInput(
            chat_history_prompt=self.conversation_manager.get_chat_history_prompt(),
            user_query=f"{kwargs['user_name']} ({kwargs['user_email']}): {kwargs['input']}",
            previous_ai_response=response,
            tool_history="\n\n".join(
                [f"{i[0]}\n**Result:** {i[1]}" for i in intermediate_steps]
            ),
            available_tool_descriptions=self.conversation_manager.get_available_tool_descriptions(
                self.tools
            ),
            loaded_documents_prompt=self.conversation_manager.get_loaded_documents_prompt(),
            selected_repository_prompt=self.conversation_manager.get_selected_repository_prompt(),
            user_settings_prompt=self.conversation_manager.get_user_settings_prompt(),
        )

        result: EvaluationOutput = self.query_helper.query_llm(
            llm=self.llm,
            input_class_instance=input_object,
            prompt_template_name="EVALUATION_TEMPLATE",
            output_class_type=EvaluationOutput,
            metadata={"output_type": "EvaluationOutput"},
        )

        return result

    def get_step_plans_or_direct_answer(self, kwargs) -> PlanningStageOutput:

        # There may be some rephrasing instructions to include in the prompt (i.e. for voice output, etc.)
        rephrase_answer_instructions_prompt = self.get_rephrase_prompt(kwargs)

        input_object = PlanningStageInput(
            system_prompt=self.conversation_manager.get_system_prompt(),
            loaded_documents_prompt=self.conversation_manager.get_loaded_documents_prompt(),
            selected_repository_prompt=self.conversation_manager.get_selected_repository_prompt(),
            previous_tool_calls_prompt=self.conversation_manager.get_previous_tool_calls_prompt(),
            available_tool_descriptions=self.conversation_manager.get_available_tool_descriptions(
                self.tools
            ),
            chat_history_prompt=self.conversation_manager.get_chat_history_prompt(),
            user_query=f"{kwargs['user_name']} ({kwargs['user_email']}): {kwargs['input']}",
            user_settings_prompt=self.conversation_manager.get_user_settings_prompt(),
            rephrase_answer_instructions_prompt=rephrase_answer_instructions_prompt,
        )

        result = self.query_helper.query_llm(
            llm=self.llm,
            input_class_instance=input_object,
            prompt_template_name="PLAN_STEPS_NO_TOOL_USE_TEMPLATE",
            output_class_type=PlanningStageOutput,
            metadata={"output_type": "PlanningStageOutput"},
        )

        return result

    def get_rephrase_prompt(self, kwargs):
        rephrase_answer_instructions_prompt = ""
        if (
            "rephrase_answer_instructions" in kwargs
            and kwargs["rephrase_answer_instructions"].strip() != ""
        ):
            rephrase_answer_instructions_prompt = (
                self.conversation_manager.prompt_manager.get_prompt_by_template_name(
                    "REPHRASE_ANSWER_INSTRUCTIONS_TEMPLATE",
                ).format(
                    rephrase_answer_instructions=kwargs["rephrase_answer_instructions"]
                )
            )

        return rephrase_answer_instructions_prompt

    def remove_steps_without_tool(self, steps, tools):
        # Create a set containing the names of tools for faster lookup
        tool_names = [tool.name for tool in tools]

        # Create a new list to store the filtered steps
        filtered_steps = []

        # Iterate over each step and check if its tool is in the set of tool names
        for step in steps:
            if step.tool.strip() == "":
                logging.error(
                    f"Step does not have a tool: {step}.  Skipping this step."
                )
                self.wrong_tool_calls.append(step)

                continue

            if step.tool in tool_names:
                filtered_steps.append(step)
            else:
                self.wrong_tool_calls.append(step)

        return filtered_steps

    def prompt_and_predict_tool_use(
        self, intermediate_steps, **kwargs: Any
    ) -> AgentAction:
        # Create the first tool use prompt
        current_step = self.planning_results.steps[self.step_index]
        tool_name = current_step.tool
        tool_details = ToolManager.get_tool_details(tool_name, self.tools)

        helpful_context = self.get_helpful_context(intermediate_steps)

        if len(self.wrong_tool_calls) > 0:
            formatted_wrong_tool_calls = "\n".join(
                [f"{p}" for p in self.wrong_tool_calls]
            )
            helpful_context += f"\n\nThe planning AI (which is supposed to plan out steps to accomplish the user's goal) came up with these invalid tool calls: {formatted_wrong_tool_calls}.\n\nPlease examine these imaginary (or incorrect) tool calls, and let them inform your tool use and eventual answer here."

            # Reset the wrong tool calls
            self.wrong_tool_calls = []

        input_object = ToolUseInput(
            selected_repository_prompt=self.conversation_manager.get_selected_repository_prompt(),
            loaded_documents_prompt=self.conversation_manager.get_loaded_documents_prompt(),
            previous_tool_calls_prompt=self.conversation_manager.get_previous_tool_calls_prompt(),
            helpful_context=helpful_context or "",
            tool_name=tool_name,
            tool_details=tool_details,
            tool_use_description=current_step.step_description,
            user_query=kwargs["input"],
            chat_history_prompt=self.conversation_manager.get_chat_history_prompt(),
            system_prompt=self.conversation_manager.get_system_prompt(),
        )

        result: ToolUseOutput = self.query_helper.query_llm(
            llm=self.llm,
            input_class_instance=input_object,
            prompt_template_name="TOOL_USE_TEMPLATE",
            output_class_type=ToolUseOutput,
            metadata={"output_type": "ToolUseOutput"},
        )

        # if "final_answer" in action_json:
        #     return AgentFinish(
        #         return_values={"output": action_json["final_answer"]},
        #         log="Agent finished, answering directly.",
        #     )

        action = AgentAction(
            tool=result.tool,
            tool_input=result.tool_args if result.tool_args else {},
            log=result.tool_use_description,
        )

        return action

    def prompt_and_predict_tool_use_retry(
        self, intermediate_steps, **kwargs: Any
    ) -> AgentAction:

        input_object = ToolUseRetryInput(
            system_prompt=self.conversation_manager.get_system_prompt(),
            loaded_documents_prompt=self.conversation_manager.get_loaded_documents_prompt(),
            selected_repository_prompt=self.conversation_manager.get_selected_repository_prompt(),
            previous_tool_calls_prompt=self.conversation_manager.get_previous_tool_calls_prompt(),
            failed_tool_attempts=self.get_tool_calls_from_failed_steps(
                intermediate_steps
            ),
            available_tool_descriptions=self.conversation_manager.get_available_tool_descriptions(
                self.tools
            ),
            user_query=kwargs["input"],
            chat_history_prompt=self.conversation_manager.get_chat_history_prompt(),
        )

        result: ToolUseOutput = self.query_helper.query_llm(
            llm=self.llm,
            input_class_instance=input_object,
            prompt_template_name="TOOL_USE_RETRY_TEMPLATE",
            output_class_type=ToolUseOutput,
            metadata={"output_type": "ToolUseOutput"},
        )

        action = AgentAction(
            tool=result.tool,
            tool_input=result.tool_args,
            log=result.tool_use_description,
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

        output = ""
        for step in intermediate_steps:
            if step[1] is not None:
                tool_results = step[1]
                # If it's a string, strip it
                if isinstance(tool_results, str):
                    tool_results = tool_results.strip()
                    
                output += f"The `{step[0].tool}` tool was used with the arguments: `{step[0].tool_input}`, which returned:\n{tool_results}\n\n"
                
        return output

    async def aplan(
        self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any
    ) -> Union[List[AgentAction], AgentFinish]:
        raise NotImplementedError("Async plan not implemented.")

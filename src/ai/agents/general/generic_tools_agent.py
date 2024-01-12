import re
import json
from typing import Any, List, Tuple, Union
import logging

from langchain.schema import AgentAction
from langchain.schema.language_model import BaseLanguageModel
from langchain.agents import AgentExecutor, BaseMultiActionAgent, BaseSingleActionAgent
from langchain.schema import AgentAction, AgentFinish
from langchain.tools import StructuredTool
from langchain.base_language import BaseLanguageModel
from src.ai.agents.general.generic_tool import GenericTool

from src.ai.llm_helper import get_llm
from src.ai.conversations.conversation_manager import ConversationManager
from src.configuration.assistant_configuration import ModelConfiguration

from src.utilities.parsing_utilities import parse_json

from src.db.models.domain.tool_call_results_model import ToolCallResultsModel


class GenericToolsAgent(BaseSingleActionAgent):
    model_configuration: ModelConfiguration = None
    conversation_manager: ConversationManager = None
    tools: list = None
    previous_work: str = None
    llm: BaseLanguageModel = None
    streaming: bool = True
    step_plans: dict = None
    step_index: int = -1
    current_retries: int = 0
    wrong_tool_calls: list = []

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
        self, intermediate_steps: Tuple[AgentAction, str], **kwargs: Any
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
        # Create the prompt with which to start the conversation (planning)
        if not intermediate_steps:
            self.llm = get_llm(
                model_configuration=self.model_configuration,
                tags=["generic_tools"],
                callbacks=self.conversation_manager.agent_callbacks,
                streaming=self.streaming,
            )

            plan_steps_prompt = self.get_plan_steps_prompt(
                user_query=kwargs["input"],
                system_information=kwargs["system_information"],
                user_name=kwargs["user_name"],
                user_email=kwargs["user_email"],
            )

            text = self.llm.predict(
                plan_steps_prompt,
                callbacks=self.conversation_manager.agent_callbacks,
            )
            # Save the step plans for future reference
            self.step_plans = parse_json(
                text,
                llm=self.llm,
            )
            # Make sure we're starting at the beginning
            self.step_index = 0

            if "final_answer" in self.step_plans:
                return AgentFinish(
                    return_values={"output": self.step_plans["final_answer"]},
                    log="Agent finished, answering directly.",
                )

        # Filter out any of the steps that use tools we don't have.
        self.step_plans["steps"] = self.remove_steps_without_tool(
            self.step_plans["steps"], self.tools
        )

        # If we still have steps to perform
        if (
            self.step_index < len(self.step_plans["steps"])
            and len(self.step_plans["steps"]) > 0
        ):
            # This is a multi-action agent, but we're going to use it sequentially for now
            # TODO: Refactor this so we can execute multiple actions at once (and handle dependencies)

            action = self.prompt_and_predict_tool_use(intermediate_steps, **kwargs)

            self.step_index += 1

            return action

        # If we're done with the steps, return the final answer
        else:
            # Construct a prompt that will return the final answer based on all of the previously returned steps/context
            answer_prompt = self.get_answer_prompt(
                user_query=kwargs["input"],
                helpful_context=self.get_helpful_context(intermediate_steps),
            )

            answer_response = self.llm.predict(
                answer_prompt, callbacks=self.conversation_manager.agent_callbacks
            )

            answer = parse_json(text=answer_response, llm=self.llm)

            # If answer is a fail, we need to retry the last step with the added context from the tool failure
            if isinstance(answer, dict):
                if "answer" in answer:
                    answer_response = answer["answer"]
                else:
                    if self.current_retries >= self.model_configuration.max_retries:
                        return AgentFinish(
                            return_values={
                                "output": "I ran out of retries attempting to answer.  Here's my last output:\n"
                                + answer_response
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

        text = self.llm.predict(
            tool_use_prompt, callbacks=self.conversation_manager.agent_callbacks
        )

        action_json = parse_json(
            text,
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
            text=self.llm.predict(
                tool_use_prompt, callbacks=self.conversation_manager.agent_callbacks
            ),
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
        system_prompt = self.get_system_prompt(system_information)
        available_tools = self.get_available_tool_descriptions(self.tools)
        loaded_documents = self.get_loaded_documents()
        chat_history = self.get_chat_history()
        previous_tool_calls = self.get_previous_tool_call_headers()

        selected_repo = self.conversation_manager.get_selected_repository()

        if selected_repo:
            selected_repo_prompt = self.conversation_manager.prompt_manager.get_prompt(
                "generic_tools_agent",
                "SELECTED_REPO_TEMPLATE",
            ).format(
                selected_repository=f"ID: {selected_repo.id} - {selected_repo.code_repository_address} ({selected_repo.branch_name})"
            )
        else:
            selected_repo_prompt = ""

        if loaded_documents:
            loaded_documents_prompt = (
                self.conversation_manager.prompt_manager.get_prompt(
                    "generic_tools_agent",
                    "LOADED_DOCUMENTS_TEMPLATE",
                ).format(loaded_documents=loaded_documents)
            )
        else:
            loaded_documents_prompt = ""

        if chat_history and len(chat_history) > 0:
            chat_history_prompt = self.conversation_manager.prompt_manager.get_prompt(
                "generic_tools_agent",
                "CHAT_HISTORY_TEMPLATE",
            ).format(chat_history=chat_history)
        else:
            chat_history_prompt = ""

        if previous_tool_calls and len(previous_tool_calls) > 0:
            previous_tool_calls_prompt = (
                self.conversation_manager.prompt_manager.get_prompt(
                    "generic_tools_agent",
                    "PREVIOUS_TOOL_CALLS_TEMPLATE",
                ).format(previous_tool_calls=previous_tool_calls)
            )
        else:
            previous_tool_calls_prompt = ""

        agent_prompt = self.conversation_manager.prompt_manager.get_prompt(
            "generic_tools_agent",
            "PLAN_STEPS_NO_TOOL_USE_TEMPLATE",
        ).format(
            system_prompt=system_prompt,
            available_tool_descriptions=available_tools,
            loaded_documents_prompt=loaded_documents_prompt,
            selected_repository_prompt=selected_repo_prompt,
            chat_history_prompt=chat_history_prompt,
            previous_tool_calls_prompt=previous_tool_calls_prompt,
            user_query=f"{user_name} ({user_email}): {user_query}",
        )

        return agent_prompt

    def get_answer_prompt(self, user_query, helpful_context):
        agent_prompt = self.conversation_manager.prompt_manager.get_prompt(
            "generic_tools_agent",
            "ANSWER_PROMPT_TEMPLATE",
        ).format(
            user_query=user_query,
            helpful_context=helpful_context,
            chat_history=self.get_chat_history(),
        )

        return agent_prompt

    def get_tool_use_prompt(
        self, step, helpful_context, user_query, system_information
    ):
        tool_name = step["tool"]
        tool_details = ""
        for tool in self.tools:
            if tool.name == tool_name:
                tool_details = self.get_tool_string(tool=tool)

        if len(self.wrong_tool_calls) > 0:
            formatted_wrong_tool_calls = "\n".join(
                [f"{p}" for p in self.wrong_tool_calls]
            )
            helpful_context = f"The planning AI (which is supposed to plan out steps to accomplish the user's goal) came up with these invalid tool calls: {formatted_wrong_tool_calls}.\n\nPlease examine these imaginary (or incorrect) tool calls, and let them inform your tool use and eventual answer here."

            # Reset the wrong tool calls
            self.wrong_tool_calls = []

        selected_repo = self.conversation_manager.get_selected_repository()
        loaded_documents = self.get_loaded_documents()
        previous_tool_calls = self.get_previous_tool_call_headers()

        if selected_repo:
            selected_repo_prompt = self.conversation_manager.prompt_manager.get_prompt(
                "generic_tools_agent",
                "SELECTED_REPO_TEMPLATE",
            ).format(
                selected_repository=f"ID: {selected_repo.id} - {selected_repo.code_repository_address} ({selected_repo.branch_name})"
            )
        else:
            selected_repo_prompt = ""

        if loaded_documents:
            loaded_documents_prompt = (
                self.conversation_manager.prompt_manager.get_prompt(
                    "generic_tools_agent",
                    "LOADED_DOCUMENTS_TEMPLATE",
                ).format(loaded_documents=loaded_documents)
            )
        else:
            loaded_documents_prompt = ""

        if previous_tool_calls and len(previous_tool_calls) > 0:
            previous_tool_calls_prompt = (
                self.conversation_manager.prompt_manager.get_prompt(
                    "generic_tools_agent",
                    "PREVIOUS_TOOL_CALLS_TEMPLATE",
                ).format(previous_tool_calls=previous_tool_calls)
            )
        else:
            previous_tool_calls_prompt = ""

        chat_history = self.get_chat_history()
        if chat_history and len(chat_history) > 0:
            chat_history_prompt = self.conversation_manager.prompt_manager.get_prompt(
                "generic_tools_agent",
                "CHAT_HISTORY_TEMPLATE",
            ).format(chat_history=chat_history)
        else:
            chat_history_prompt = ""

        agent_prompt = self.conversation_manager.prompt_manager.get_prompt(
            "generic_tools_agent",
            "TOOL_USE_TEMPLATE",
        ).format(
            selected_repository_prompt=selected_repo_prompt,
            loaded_documents_prompt=loaded_documents_prompt,
            helpful_context=helpful_context,
            tool_name=tool_name,
            tool_details=tool_details,
            tool_use_description=step["step_description"],
            user_query=user_query,
            chat_history_prompt=chat_history_prompt,
            previous_tool_calls_prompt=previous_tool_calls_prompt,
            system_prompt=self.get_system_prompt(
                system_information,
            ),
        )

        return agent_prompt

    def get_tool_use_retry_prompt(
        self, step, previous_tool_attempts, user_query, system_information
    ):
        available_tools = self.get_available_tool_descriptions(self.tools)

        agent_prompt = self.conversation_manager.prompt_manager.get_prompt(
            "generic_tools_agent",
            "TOOL_USE_RETRY_TEMPLATE",
        ).format(
            loaded_documents=self.get_loaded_documents(),
            previous_tool_attempts=previous_tool_attempts,
            available_tool_descriptions=available_tools,
            tool_use_description=step["step_description"],
            user_query=user_query,
            chat_history=self.get_chat_history(),
            system_prompt=self.get_system_prompt(system_information),
        )

        return agent_prompt

    def get_system_prompt(self, system_information):
        system_prompt = self.conversation_manager.prompt_manager.get_prompt(
            "generic_tools_agent",
            "SYSTEM_TEMPLATE",
        ).format(
            system_information=system_information,
        )

        return system_prompt

    def get_previous_tool_call_headers(self):
        previous_tool_calls: List[
            ToolCallResultsModel
        ] = self.conversation_manager.conversations_helper.get_tool_call_results(
            self.conversation_manager.conversation_id
        )

        if not previous_tool_calls or len(previous_tool_calls) == 0:
            return None

        return "\n".join(
            [
                f"{tool_call.record_created} - (ID: {tool_call.id}) Name: `{tool_call.tool_name}`, tool input: {tool_call.tool_arguments}"
                for tool_call in previous_tool_calls
            ]
        )

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

            if tool.document_classes:
                classes = ", ".join(tool.document_classes)
                document_class = f"\nIMPORTANT: Only use this tool with documents with classifications of: '{classes}'. For other types of files, refer to specialized tools."
            else:
                document_class = ""

            tool_strings.append(
                f"Name: {tool.name}\nDescription: {tool.description}{additional_instructions}{document_class}"
            )

        formatted_tools = "\n----\n".join(tool_strings)

        return formatted_tools

    def get_loaded_documents(self):
        if self.conversation_manager:
            return "\n".join(
                self.conversation_manager.get_loaded_documents_for_reference()
            )
        else:
            return None

    def get_chat_history(self):
        if self.conversation_manager:
            return (
                self.conversation_manager.conversation_token_buffer_memory.buffer_as_str
            )
        else:
            return "No chat history."

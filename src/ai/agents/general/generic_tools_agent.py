import re
import logging
from typing import Any, List, Optional, Sequence, Tuple

from langchain.agents.agent import Agent, AgentOutputParser
from langchain.agents.structured_chat.output_parser import (
    StructuredChatOutputParserWithRetries,
)
from langchain.agents.structured_chat.prompt import FORMAT_INSTRUCTIONS, PREFIX, SUFFIX
from langchain.callbacks.base import BaseCallbackManager
from langchain.chains.llm import LLMChain
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.pydantic_v1 import Field
from langchain.schema import AgentAction, BasePromptTemplate
from langchain.schema.language_model import BaseLanguageModel
from langchain.tools import BaseTool
import sys
import os
import re
import json
from typing import Any, List, Tuple, Union


from langchain.agents import (
    Tool,
    AgentExecutor,
    BaseMultiActionAgent,
    BaseSingleActionAgent,
)
from langchain.schema import AgentAction, AgentFinish
from langchain.tools import StructuredTool
from langchain.base_language import BaseLanguageModel

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)

from src.ai.llm_helper import get_prompt, get_llm

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

from src.ai.interactions.interaction_manager import InteractionManager

from src.configuration.assistant_configuration import ModelConfiguration


class GenericTool:
    def __init__(self, description, function, return_direct=False, additional_instructions=None):
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


class GenericToolsAgent(BaseSingleActionAgent):
    model_configuration: ModelConfiguration = None
    interaction_manager: InteractionManager = None
    tools: list = None
    previous_work: str = None
    llm: BaseLanguageModel = None
    steps: dict = None
    current_step_index: int = 0
    callbacks: list = None
    streaming: bool = True

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
        # Create the prompt with which to start the conversation
        # Then run the first call to the LLM
        if not intermediate_steps:
            self.llm = get_llm(
                model_configuration=self.model_configuration,
                tags=["generic_tools"],
                callbacks=kwargs['callbacks'],
                streaming=self.streaming,
            )
            self.current_step_index = 0
        else:
            self.current_step_index += 1

            # Use the create steps prompt to create a list of all of the forseen steps
        agent_prompt = self.get_split_steps_prompt(
            user_query=kwargs["input"],
            system_information=kwargs["system_information"],
            user_name=kwargs["user_name"],
            user_email=kwargs["user_email"],
            intermediate_steps=intermediate_steps,
        )

        step_response = self.llm.predict(agent_prompt)

        step = self.parse_json(step_response)

        if "step_description" in step:
            if step["tool"] != "final_answer":
                return AgentAction(
                    tool=step["tool"],
                    tool_input=step["tool_args"] if "tool_args" in step else {},
                    log=step["step_description"],
                )
            else:
                return AgentFinish(return_values={"output": step["tool_args"]['answer']}, log="Agent finished.")
        else:
            logging.warning("Got unexpected response from LLM: %s", step_response)
            return AgentFinish(
                return_values={"output": step_response},
                log="Agent finished (but with parsing issues).",
            )

    async def aplan(
        self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any
    ) -> Union[AgentAction, AgentFinish]:
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

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        pattern = re.compile(r"```(?:json)?\n(.*?)```", re.DOTALL)
        try:
            action_match = pattern.search(text)
            if action_match is not None:
                response = json.loads(action_match.group(1).strip(), strict=False)
                if isinstance(response, list):
                    # Not supported at the moment, but should be easy enough to add
                    logging.warning("Got multiple action responses: %s", response)
                    response = response[0]
                if response["action"] == "final_answer":
                    return AgentFinish({"output": response["action_input"]}, text)
                else:
                    return AgentAction(
                        response["action"], response.get("action_input", {}), text
                    )
            else:
                return AgentFinish({"output": text}, text)
        except Exception as e:
            raise Exception(f"Could not parse LLM output: {text}") from e

    def get_previous_steps(self, intermediate_steps):
        if not intermediate_steps or len(intermediate_steps) == 0:
            return ""

        previous_steps = "\n----\n".join(
            [
                f"I used the '{s[0].tool}' tool to perform the step: '{s[0].log}', and received the following response (make sure to take this into consideration):\n{s[1]}"
                for s in intermediate_steps
            ]
        )
        return (
            "\n--- COMPLETED STEPS --- \n"
            + previous_steps
            + "\n--- COMPLETED STEPS --- \n"
        )

    def get_answered_steps_hint(self, intermediate_steps):
        if not intermediate_steps or len(intermediate_steps) == 0:
            return ""

        answered_steps_hint = "I can see that some work has already been done (in COMPLETED STEPS), and I will take it into consideration when determining whether to answer or provide another step to take. The work that was done so far is:\n- "
        answered_steps_hint += "\n- ".join(
            [
                f"I used the '{s[0].tool}' tool to perform the step: '{s[0].log}'"
                for s in intermediate_steps
            ]
        )
        return "\n" + answered_steps_hint + "\n"

    def get_split_steps_prompt(
        self, user_query, system_information, user_name, user_email, intermediate_steps
    ):
        system_prompt = self.get_system_prompt(
            "Detail oriented, organized, and logical.", system_information
        )
        available_tools = self.get_available_tools(self.tools)
        loaded_documents = self.get_loaded_documents()
        chat_history = self.get_chat_history()

        agent_prompt = get_prompt(
            self.model_configuration.llm_type,
            "SPLIT_STEPS_TEMPLATE",
        ).format(
            system_prompt=system_prompt,
            available_tools=available_tools,
            loaded_documents=loaded_documents,
            chat_history=chat_history,
            user_query=f"{user_name} ({user_email}): {user_query}",
            previous_steps=self.get_previous_steps(intermediate_steps),
            answered_steps_hint=self.get_answered_steps_hint(intermediate_steps),
        )

        return agent_prompt

    def get_agent_prompt(self, user_query, system_information, user_name, user_email):
        system_prompt = self.get_system_prompt(
            "Detail oriented, organized, and logical.", system_information
        )
        available_tools = self.get_available_tools(self.tools)
        response_formatting_instructions = self.get_response_formatting_instructions()
        loaded_documents = self.get_loaded_documents()
        chat_history = self.get_chat_history()
        agent_instructions = self.get_agent_instructions()
        examples = self.get_examples()

        agent_prompt = get_prompt(
            self.model_configuration.llm_type,
            "AGENT_PROMPT_TEMPLATE",
        ).format(
            system_prompt=system_prompt,
            available_tools=available_tools,
            response_formatting_instructions=response_formatting_instructions,
            loaded_documents=loaded_documents,
            chat_history=chat_history,
            agent_instructions=agent_instructions,
            examples=examples,
            user_query=f"{user_name} ({user_email}): {user_query}",
        )

        return agent_prompt

    def get_agent_round_n_prompt(self, previous_work, observation):
        agent_round_n_prompt = get_prompt(
            self.model_configuration.llm_type,
            "AGENT_ROUND_N_TEMPLATE",
        ).format(
            previous_work=previous_work,
            observation=observation,
            tool_names=[f'"{t.name}"' for t in self.tools],
        )

        return agent_round_n_prompt

    def get_system_prompt(self, personality_descriptors, system_information):
        system_prompt = get_prompt(
            self.model_configuration.llm_type,
            "SYSTEM_TEMPLATE",
        ).format(
            personality_descriptors=personality_descriptors,
            system_information=system_information,
        )

        return system_prompt

    def get_available_tools(self, tools: list[GenericTool]):
        tool_strings = []
        for tool in tools:
            args_schema = "\n\t".join(
                [
                    f"{t['argument_name']}, {t['argument_type']}, {t['required']}"
                    for t in tool.schema["parameters"]
                ]
            )
            if tool.additional_instructions:
                additional_instructions = "\nAdditional Instructions: " + tool.additional_instructions
            else:
                additional_instructions = ""

            tool_strings.append(
                f"Name: {tool.name}\nDescription: {tool.description}{additional_instructions}\nArgs (name, type, optional/required):\n\t{args_schema}"
            )

        formatted_tools = "\n----\n".join(tool_strings)

        return formatted_tools

    def get_response_formatting_instructions(self):
        response_formatting_instructions = get_prompt(
            self.model_configuration.llm_type,
            "RESPONSE_FORMATTING_TEMPLATE",
        )

        return response_formatting_instructions

    def get_loaded_documents(self):
        if self.interaction_manager:
            return "\n".join(self.interaction_manager.get_loaded_documents_for_reference())
        else:
            return "No documents loaded."

    def get_chat_history(self):
        if self.interaction_manager:
            return (
                self.interaction_manager.conversation_token_buffer_memory.buffer_as_str
            )
        else:
            return "No chat history."

    def get_agent_instructions(self):
        response_formatting_instructions = get_prompt(
            self.model_configuration.llm_type,
            "AGENT_INSTRUCTIONS_TEMPLATE",
        )

        return response_formatting_instructions

    def get_examples(self):
        stand_alone_example = get_prompt(
            self.model_configuration.llm_type,
            "STAND_ALONE_EXAMPLE",
        )

        single_hop_example = get_prompt(
            self.model_configuration.llm_type,
            "SINGLE_HOP_EXAMPLE",
        )

        multi_hop_example = get_prompt(
            self.model_configuration.llm_type,
            "MULTI_HOP_EXAMPLE",
        )

        return f"{stand_alone_example}\n\n{single_hop_example}\n\n{multi_hop_example}"


# Testing
if __name__ == "__main__":
    from src.tools.documents.document_tool import DocumentTool
    from src.tools.code.code_tool import CodeTool

    document_tool = DocumentTool(None, None, None)
    code_tool = CodeTool(None, None, None)

    tool_functions = [
        GenericTool(
            description="Searches the loaded documents for the specified query.",
            function=document_tool.search_loaded_documents,
        ),
        GenericTool(
            description="Summarizes the entire document.",
            function=document_tool.summarize_entire_document,
        ),
        GenericTool(
            description="Gets the details of the specified code.",
            function=code_tool.code_details,
        ),
    ]

    agent = GenericToolsAgent(
        tools=[],
        model_configuration=ModelConfiguration(
            llm_type="openai",
            model="gpt-3.5-turbo-16k",
            temperature=0,
            max_retries=3,
            max_model_supported_tokens=16384,
            max_conversation_history_tokens=8192,
            max_completion_tokens=6096,
        ),
    )

    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent, tools=[], verbose=True
    )

    response = agent_executor.run(user_query="What is the temperature of the sun?")

    agent = GenericToolsAgent(
        tools=tool_functions,
        model_configuration=ModelConfiguration(
            llm_type="openai",
            model="gpt-3.5-turbo-16k",
            temperature=0,
            max_retries=3,
            max_model_supported_tokens=16384,
            max_conversation_history_tokens=8192,
            max_completion_tokens=6096,
        ),
    )

    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent, tools=[t.structured_tool for t in tool_functions], verbose=True
    )

    print(response)

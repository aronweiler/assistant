from __future__ import annotations

from typing import TypeVar

from langchain.chains.llm import LLMChain
from langchain.output_parsers.prompts import NAIVE_FIX_PROMPT
from langchain.schema import BaseOutputParser, BasePromptTemplate, OutputParserException
from langchain.schema.language_model import BaseLanguageModel

T = TypeVar("T")

import json
import logging
import re
from typing import Optional, Union

from langchain.agents.agent import AgentOutputParser
from langchain.agents.structured_chat.prompt import FORMAT_INSTRUCTIONS
#from langchain.output_parsers import OutputFixingParser
from langchain.pydantic_v1 import Field
from langchain.schema import AgentAction, AgentFinish, OutputParserException
from langchain.schema.language_model import BaseLanguageModel

logger = logging.getLogger(__name__)


class CustomStructuredChatOutputParser(AgentOutputParser):
    """Output parser for the structured chat agent."""

    pattern = re.compile(r"```(?:json)?\n(.*?)```", re.DOTALL)

    def get_format_instructions(self) -> str:
        return FORMAT_INSTRUCTIONS

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        try:
            action_match = self.pattern.search(text)
            if action_match is not None:
                response = json.loads(action_match.group(1).strip(), strict=False)
                if isinstance(response, list):
                    # gpt turbo frequently ignores the directive to emit a single action
                    logger.warning("Got multiple action responses: %s", response)
                    response = response[0]
                if response["action"] == "Final Answer":
                    return AgentFinish({"output": response["action_input"]}, text)
                else:
                    return AgentAction(
                        response["action"], response.get("action_input", {}), text
                    )
            else:
                return AgentFinish({"output": text}, text)
        except Exception as e:
            raise OutputParserException(f"Could not parse LLM output: {text}") from e

    @property
    def _type(self) -> str:
        return "structured_chat"


class CustomOutputFixingParser(AgentOutputParser):
    def parse(self, text):
        return text


class CustomStructuredChatOutputParserWithRetries(AgentOutputParser):
    """Output parser with retries for the structured chat agent."""

    base_parser: AgentOutputParser = Field(
        default_factory=CustomStructuredChatOutputParser
    )
    """The base parser to use."""
    output_fixing_parser: OutputFixingParser = None# Optional[OutputFixingParser] = None
    """The output fixing parser to use."""

    # def __init__(
    #     self,
    #     base_parser: AgentOutputParser = Field(
    #         default_factory=CustomStructuredChatOutputParser
    #     ),
    #     output_fixing_parser: Optional[OutputFixingParser] = None,
    # ):
    #     self.base_parser = base_parser
    #     self.output_fixing_parser = output_fixing_parser
    #     logging.info("__init__ CustomStructuredChatOutputParserWithRetries")

    def get_format_instructions(self) -> str:
        return FORMAT_INSTRUCTIONS

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        try:
            if self.output_fixing_parser is not None:
                parsed_obj: Union[
                    AgentAction, AgentFinish
                ] = self.output_fixing_parser.parse(text)
            else:
                parsed_obj = self.base_parser.parse(text)
            return parsed_obj
        except Exception as e:
            raise OutputParserException(f"Could not parse LLM output: {text}") from e

    @classmethod
    def from_llm(
        cls,
        llm: Optional[BaseLanguageModel] = None,
        base_parser: Optional[CustomStructuredChatOutputParser] = None,
    ) -> CustomStructuredChatOutputParserWithRetries:
        logging.info("Creating CustomStructuredChatOutputParserWithRetries.from_llm")

        if llm is not None:
            base_parser = base_parser or CustomStructuredChatOutputParser()
            logging.info("Using output fixing parser from LLM")
            output_fixing_parser = OutputFixingParser.from_llm(
                llm=llm, parser=base_parser
            )
            logging.info("Creating CustomStructuredChatOutputParserWithRetries")
            return cls(output_fixing_parser=output_fixing_parser)
        elif base_parser is not None:
            return cls(base_parser=base_parser)
        else:
            return cls()

    @property
    def _type(self) -> str:
        return "structured_chat_with_retries"


class OutputFixingParser(BaseOutputParser[T]):
    """Wraps a parser and tries to fix parsing errors."""

    @property
    def lc_serializable(self) -> bool:
        return True

    parser: BaseOutputParser[T]
    retry_chain: LLMChain

    @classmethod
    def from_llm(
        cls,
        llm: BaseLanguageModel,
        parser: BaseOutputParser[T],
        prompt: BasePromptTemplate = NAIVE_FIX_PROMPT,
    ) -> OutputFixingParser[T]:
        """Create an OutputFixingParser from a language model and a parser.

        Args:
            llm: llm to use for fixing
            parser: parser to use for parsing
            prompt: prompt to use for fixing

        Returns:
            OutputFixingParser
        """
        logging.info("Creating OutputFixingParser.from_llm")
        chain = LLMChain(llm=llm, prompt=prompt)
        logging.info("Creating OutputFixingParser")
        return cls(parser=parser, retry_chain=chain)

    def parse(self, completion: str) -> T:
        try:
            parsed_completion = self.parser.parse(completion)
        except OutputParserException as e:
            new_completion = self.retry_chain.run(
                instructions=self.parser.get_format_instructions(),
                completion=completion,
                error=repr(e),
            )
            parsed_completion = self.parser.parse(new_completion)

        return parsed_completion

    async def aparse(self, completion: str) -> T:
        try:
            parsed_completion = self.parser.parse(completion)
        except OutputParserException as e:
            new_completion = await self.retry_chain.arun(
                instructions=self.parser.get_format_instructions(),
                completion=completion,
                error=repr(e),
            )
            parsed_completion = self.parser.parse(new_completion)

        return parsed_completion

    def get_format_instructions(self) -> str:
        return self.parser.get_format_instructions()

    @property
    def _type(self) -> str:
        return "output_fixing"

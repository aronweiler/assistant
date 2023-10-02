import time
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Union

from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult

class ResultOnlyCallbackHandler(BaseCallbackHandler):
    response: LLMResult

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        self.response = response
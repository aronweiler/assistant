import threading
from typing import Any, Dict, List, Optional, Union
from langchain.callbacks.base import BaseCallbackHandler

from streamlit.delta_generator import DeltaGenerator
from streamlit.elements.lib.mutable_status_container import StatusContainer


class StreamlitStreamingOnlyCallbackHandler(BaseCallbackHandler):
    def __init__(self, container: DeltaGenerator):
        self.container = container
        self.text = ""

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        try:
            self.container.markdown(self.text)
        except:
            # Sometimes the control goes away because we switch pages
            pass


class VoiceToolUsingCallbackHandler(BaseCallbackHandler):
    def __init__(self, speak_function) -> None:
        self.speak_function = speak_function
        self._current_thought: Optional[str] = None

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        print("LLM START")
        # Create a thread to call the speak function

        output_type = None
        if "metadata" in kwargs and "output_type" in kwargs["metadata"]:
            output_type = kwargs["metadata"]["output_type"]

        # Only speak on llm_start if the output type is PlanningStageOutput
        if output_type == "PlanningStageOutput":
            thread = threading.Thread(
                target=self.speak_function,
                args=(
                    "Let me think about that for a moment, I might have to use some tools...",
                ),
            )
            thread.start()

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        print(token, end="")

    def on_llm_end(self, response, **kwargs: Any) -> None:
        print("LLM COMPLETE")

    def on_llm_error(self, error: BaseException, *args: Any, **kwargs: Any) -> None:
        print("LLM ERROR")

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        print("TOOL START")

    def on_tool_end(
        self,
        output: str,
        color: Optional[str] = None,
        observation_prefix: Optional[str] = None,
        llm_prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        print(output)

    def on_tool_error(self, error: BaseException, *args: Any, **kwargs: Any) -> None:
        print("TOOL ERROR")

    def on_agent_action(
        self, action, color: Optional[str] = None, **kwargs: Any
    ) -> Any:
        thread = threading.Thread(
            target=self.speak_function, args=(f"I am going to {action.log}",)
        )
        thread.start()

    def on_agent_finish(
        self, finish, color: Optional[str] = None, **kwargs: Any
    ) -> None:
        print(finish)

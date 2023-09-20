import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from typing import Any, Dict, List, Union, Optional

from langchain.agents.agent import AgentAction, AgentFinish
from langchain.callbacks.base import BaseCallbackHandler

class StreamingOnlyCallbackHandler(BaseCallbackHandler):
    def __init__(self, container:DeltaGenerator):
        self.container = container
        self.text = ""

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token

        self.container.markdown(self.text)


class StreamlitStreamHandler(BaseCallbackHandler):
    def __init__(self, container:DeltaGenerator):
        self.container = container
        self.log_expander = self.container.expander("Log 📒", expanded=True)
        #self.stream_expander = self.container.expander("Stream ⏳", expanded=False).empty()        
        self.text = ""

    # def on_llm_new_token(self, token: str, **kwargs) -> None:
    #     self.text += token

    #     self.stream_expander.write(self.text)

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        with self.log_expander:
            st.write(f"Starting LLM ({serialized['kwargs']['model']})...")

    def on_llm_end(self, response: str, **kwargs: Any) -> None:
        with self.log_expander:
            st.write("LLM Action Complete")

    def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        with self.log_expander:
            st.write(str(error))

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        with self.log_expander:
            st.write(f"Starting Tool {serialized['name']}...")

    def on_tool_end(
        self,
        output: str,
        color: Optional[str] = None,
        observation_prefix: Optional[str] = None,
        llm_prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        with self.log_expander:
            st.write("Tool complete")

    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        with self.log_expander:
            st.write(str(error))

    def on_agent_action(
        self, action: AgentAction, color: Optional[str] = None, **kwargs: Any
    ) -> Any:
        with self.log_expander:
            st.write(action.log)

    def on_agent_finish(
        self, finish: AgentFinish, color: Optional[str] = None, **kwargs: Any
    ) -> None:
        with self.log_expander:
            st.write(finish.log)


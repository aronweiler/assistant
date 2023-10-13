from langchain.callbacks.base import BaseCallbackHandler

from streamlit.delta_generator import DeltaGenerator
from streamlit.elements.lib.mutable_status_container import StatusContainer


class StreamingOnlyCallbackHandler(BaseCallbackHandler):
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

from typing import Any, Dict, List, Optional, Union
from streamlit.delta_generator import DeltaGenerator
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.streamlit.streamlit_callback_handler import LLMThoughtLabeler, LLMThought, LLMResult, AgentAction, AgentFinish

class StreamlitAgentCallbackHandler(BaseCallbackHandler):
    def __init__(
        self,
        parent_container: DeltaGenerator,
        *,
        max_thought_containers: int = 4,
        expand_new_thoughts: bool = False,
        collapse_completed_thoughts: bool = False,
        thought_labeler: Optional[LLMThoughtLabeler] = None,
    ):
        """Construct a new StreamlitCallbackHandler. This CallbackHandler is geared
        towards use with a LangChain Agent; it displays the Agent's LLM and tool-usage
        "thoughts" inside a series of Streamlit expanders.

        Parameters
        ----------

        parent_container
            The `st.container` that will contain all the Streamlit elements that the
            Handler creates.

        max_thought_containers

            .. note::
                This parameter is deprecated and is ignored in the latest version of
                the callback handler.

            The max number of completed LLM thought containers to show at once. When
            this threshold is reached, a new thought will cause the oldest thoughts to
            be collapsed into a "History" expander. Defaults to 4.

        expand_new_thoughts
            Each LLM "thought" gets its own `st.expander`. This param controls whether
            that expander is expanded by default. Defaults to False.

        collapse_completed_thoughts
            If True, LLM thought expanders will be collapsed when completed.
            Defaults to False.

        thought_labeler
            An optional custom LLMThoughtLabeler instance. If unspecified, the handler
            will use the default thought labeling logic. Defaults to None.
        """
        self._parent_container = parent_container
        self._history_parent = parent_container.container()
        self._current_thought: Optional[LLMThought] = None
        self._completed_thoughts: List[LLMThought] = []
        self._max_thought_containers = max(max_thought_containers, 1)
        self._expand_new_thoughts = expand_new_thoughts
        self._collapse_completed_thoughts = collapse_completed_thoughts
        self._thought_labeler = thought_labeler or LLMThoughtLabeler()

    def _require_current_thought(self) -> LLMThought:
        """Return our current LLMThought. Raise an error if we have no current
        thought.
        """
        if self._current_thought is None:
            raise RuntimeError("Current LLMThought is unexpectedly None!")
        return self._current_thought

    def _get_last_completed_thought(self) -> Optional[LLMThought]:
        """Return our most recent completed LLMThought, or None if we don't have one."""
        if len(self._completed_thoughts) > 0:
            return self._completed_thoughts[len(self._completed_thoughts) - 1]
        return None

    def _complete_current_thought(self, final_label: Optional[str] = None) -> None:
        """Complete the current thought, optionally assigning it a new label.
        Add it to our _completed_thoughts list.
        """
        thought = self._require_current_thought()
        thought.complete(final_label)
        self._completed_thoughts.append(thought)
        self._current_thought = None

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        if self._current_thought is None:
            self._current_thought = LLMThought(
                parent_container=self._parent_container,
                expanded=self._expand_new_thoughts,
                collapse_on_complete=self._collapse_completed_thoughts,
                labeler=self._thought_labeler,
            )

        self._current_thought.on_llm_start(serialized, prompts)

        # We don't prune_old_thought_containers here, because our container won't
        # be visible until it has a child.

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self._require_current_thought().on_llm_new_token(token, **kwargs)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        self._require_current_thought().on_llm_end(response, **kwargs)        

    def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        self._require_current_thought().on_llm_error(error, **kwargs)

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        self._require_current_thought().on_tool_start(serialized, input_str, **kwargs)

    def on_tool_end(
        self,
        output: str,
        color: Optional[str] = None,
        observation_prefix: Optional[str] = None,
        llm_prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self._require_current_thought().on_tool_end(
            output, color, observation_prefix, llm_prefix, **kwargs
        )
        self._complete_current_thought()

    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        self._require_current_thought().on_tool_error(error, **kwargs)

    def on_agent_action(
        self, action: AgentAction, color: Optional[str] = None, **kwargs: Any
    ) -> Any:
        self._require_current_thought().on_agent_action(action, color, **kwargs)

    def on_agent_finish(
        self, finish: AgentFinish, color: Optional[str] = None, **kwargs: Any
    ) -> None:
        print(f"on_agent_finish, finish: {finish}, color: {color}, kwargs: {kwargs}")
        if self._current_thought is not None:
            self._current_thought.complete(
                self._thought_labeler.get_final_agent_thought_label()
            )
            self._current_thought = None

        self._parent_container.markdown(finish.return_values["output"])
import logging
from langchain.callbacks.base import BaseCallbackHandler 
from langchain.memory import ConversationBufferMemory
from langchain.schema import AIMessage, HumanMessage

class AgentCallback(BaseCallbackHandler):
    memory:ConversationBufferMemory
     
    def on_tool_start(
        self,
        serialized,
        input_str: str,
        *,
        run_id,
        parent_run_id,
        tags,
        metadata,
        **kwargs
    ):

        """Run when tool starts running."""
        logging.debug(f"Tool input: {input_str}")

        self.memory.chat_memory.messages.append(AIMessage(content=f"{serialized['name']} called with {input_str}"))

    # def on_tool_end(
    #     self,
    #     output: str,
    #     *,
    #     run_id,
    #     parent_run_id,
    #     **kwargs,
    # ):
    #     """Run when tool ends running."""
    #     logging.debug(f"Tool output: {output}")

    def on_tool_end(self, output: str, **kwargs):
        """Run when tool ends running."""
        logging.debug(f"Tool output: {output}")

        self.memory.chat_memory.messages.append(AIMessage(content=output))

    def on_tool_error(
        self,
        error,
        *,
        run_id,
        parent_run_id,
        **kwargs,
    ):
        """Run when tool errors."""
        logging.exception(error) 
        

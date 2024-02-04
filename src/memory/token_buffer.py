## Taken from langchain... had to modify this to allow me to prune stored messages on retrieval,
# not have the pruning occur on savecontext. Should probably create a PR or something.

from functools import lru_cache
from typing import Any, Dict, List

from langchain.memory.chat_memory import BaseChatMemory
from langchain.schema.language_model import BaseLanguageModel
from langchain.schema.messages import BaseMessage, get_buffer_string


class ConversationTokenBufferMemory(BaseChatMemory):
    """Conversation chat memory with token limit."""

    human_prefix: str = "Human"
    ai_prefix: str = "AI"
    memory_key: str = "history"
    max_token_limit: int = 2000

    @property
    def buffer(self) -> Any:
        """String buffer of memory."""
        return self.buffer_as_messages if self.return_messages else self.buffer_as_str

    @property
    def buffer_as_str(self) -> str:
        """Exposes the buffer as a string in case return_messages is True."""
        return get_buffer_string(
            self.get_messages(),
            human_prefix=self.human_prefix,
            ai_prefix=self.ai_prefix,
        )

    @property
    def buffer_as_messages(self) -> List[BaseMessage]:
        """Exposes the buffer as a list of messages in case return_messages is False."""
        return self.get_messages()

    @property
    def memory_variables(self) -> List[str]:
        """Will always return list of memory variables.

        :meta private:
        """
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Return history buffer."""
        return {self.memory_key: self.buffer}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Save context from this conversation to buffer. Pruned."""
        super().save_context(inputs, outputs)

    def get_messages(self):
        # Prune buffer if it exceeds max token limit
        buffer = self.chat_memory.messages
        curr_buffer_length = self.get_num_tokens_from_messages(buffer)
        if curr_buffer_length > self.max_token_limit:
            pruned_memory = []
            while curr_buffer_length > self.max_token_limit:
                pruned_memory.append(buffer.pop(0))
                curr_buffer_length = self.get_num_tokens_from_messages(buffer)

        return buffer

    def get_num_tokens(self, text: str) -> int:
        # get the cached tokenizer
        tokenizer = get_tokenizer()

        # tokenize the text using the GPT-2 tokenizer
        tokens = tokenizer.encode(text)

        return len(tokens)

    def get_num_tokens_from_messages(self, messages: List[BaseMessage]) -> int:
        """Get the number of tokens in the messages.

        Useful for checking if an input will fit in a model's context window.

        Args:
            messages: The message inputs to tokenize.

        Returns:
            The sum of the number of tokens across the messages.
        """
        return sum([self.get_num_tokens(get_buffer_string([m])) for m in messages])


@lru_cache(maxsize=None)  # Cache the tokenizer
def get_tokenizer() -> Any:
    try:
        from transformers import GPT2TokenizerFast  # type: ignore[import]
    except ImportError:
        raise ImportError(
            "Could not import transformers python package. "
            "This is needed in order to calculate get_token_ids. "
            "Please install it with `pip install transformers`."
        )
    # create a GPT-2 tokenizer instance
    return GPT2TokenizerFast.from_pretrained("gpt2")

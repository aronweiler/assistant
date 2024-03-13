from typing import List
from typing import (
    Dict,
    Any,
    List,
)
from pydantic import Field
from langchain.memory.chat_memory import BaseChatMemory
from langchain.memory.entity import BaseEntityStore
from langchain.base_language import BaseLanguageModel
from langchain.chains import LLMChain

from langchain.schema.messages import BaseMessage
from langchain.memory.utils import get_prompt_input_key

from langchain.prompts import BasePromptTemplate
from langchain.schema.messages import get_buffer_string
from langchain.memory.entity import InMemoryEntityStore

from src.shared.ai.memory.prompts import (
    ENTITY_EXTRACTION_PROMPT,
    ENTITY_SUMMARIZATION_PROMPT,
    WORTHINESS_EVALUATION_PROMPT,
)


# A custom version of the langchain implementation of the ConversationEntityMemory class
class CustomConversationEntityMemory(BaseChatMemory):
    """Entity extractor & summarizer memory.

    Extracts named entities from the recent chat history and generates summaries.
    With a swappable entity store, persisting entities across conversations.
    Defaults to an in-memory entity store, and can be swapped out for a Redis,
    SQLite, or other entity store.
    """

    human_prefix: str = "Human"
    ai_prefix: str = "AI"
    llm: BaseLanguageModel
    entity_extraction_prompt: BasePromptTemplate = ENTITY_EXTRACTION_PROMPT
    entity_summarization_prompt: BasePromptTemplate = ENTITY_SUMMARIZATION_PROMPT
    worthiness_evaluation_prompt: BasePromptTemplate = WORTHINESS_EVALUATION_PROMPT

    # Cache of recently detected entity names, if any
    # It is updated when load_memory_variables is called:
    entity_cache: List[str] = []

    # Number of recent message pairs to consider when updating entities:
    k: int = 3

    chat_history_key: str = "history"

    # Store to manage entity-related data:
    entity_store: BaseEntityStore = Field(default_factory=InMemoryEntityStore)

    @property
    def buffer(self) -> List[BaseMessage]:
        """Access chat memory messages."""
        return self.chat_memory.messages

    @property
    def memory_variables(self) -> List[str]:
        """Will always return list of memory variables.

        :meta private:
        """
        return ["entities", self.chat_history_key]

    def transform_dict_to_string(self, input_dict):
        entity_to_desc = {}

        for entity, descriptions in input_dict.items():
            for description in descriptions:
                if description not in entity_to_desc:
                    entity_to_desc[description] = [entity]
                else:
                    entity_to_desc[description].append(entity)

        result_string = ""
        for description, entities in entity_to_desc.items():
            entities_str = ", ".join(entities)
            result_string += f"{entities_str}: {description}\n"

        return result_string

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns chat history and all generated entities with summaries if available,
        and updates or clears the recent entity cache.

        New entity name can be found when calling this method, before the entity
        summaries are generated, so the entity cache values may be empty if no entity
        descriptions are generated yet.
        """

        # Create an LLMChain for predicting entity names from the recent chat history:
        chain = LLMChain(llm=self.llm, prompt=self.entity_extraction_prompt)

        if self.input_key is None:
            prompt_input_key = get_prompt_input_key(inputs, self.memory_variables)
        else:
            prompt_input_key = self.input_key

        # Extract an arbitrary window of the last message pairs from
        # the chat history, where the hyperparameter k is the
        # number of message pairs:
        buffer_string = get_buffer_string(
            self.buffer[-self.k * 2 :],
            human_prefix=self.human_prefix,
            ai_prefix=self.ai_prefix,
        )

        # Generates a comma-separated list of named entities,
        # e.g. "Jane, White House, UFO"
        # or "NONE" if no named entities are extracted:
        output = chain.predict(
            history=buffer_string,
            input=inputs[prompt_input_key],
            human_prefix=self.human_prefix,
        )

        # If no named entities are extracted, assigns an empty list.
        if output.strip() == "NONE":
            entities = []
        else:
            # Make a list of the extracted entities:
            entities = [w.strip() for w in output.split(",")]

        # Make a dictionary of entities with summary if exists:
        entity_summaries = {}
        entity_summary_list = []

        for entity in entities:
            entity_summary_list.append(self.entity_store.get(entity, None))
            entity_summaries[entity] = [s for s in entity_summary_list][0]

        entity_summary = self.transform_dict_to_string(entity_summaries)

        # Replaces the entity name cache with the most recently discussed entities,
        # or if no entities were extracted, clears the cache:
        self.entity_cache = entities

        # Should we return as message objects or as a string?
        if self.return_messages:
            # Get last `k` pair of chat messages:
            buffer: Any = self.buffer[-self.k * 2 :]
        else:
            # Reuse the string we made earlier:
            buffer = buffer_string

        return {
            self.chat_history_key: buffer,
            "entities": entity_summary,
        }

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """
        Save context from this conversation history to the entity store.

        Generates a summary for each entity in the entity cache by prompting
        the model, and saves these summaries to the entity store.
        """

        super().save_context(inputs, outputs)

        if self.input_key is None:
            prompt_input_key = get_prompt_input_key(inputs, self.memory_variables)
        else:
            prompt_input_key = self.input_key

        # Extract an arbitrary window of the last message pairs from
        # the chat history, where the hyperparameter k is the
        # number of message pairs:
        buffer_string = get_buffer_string(
            self.buffer[-self.k * 2 :],
            human_prefix=self.human_prefix,
            ai_prefix=self.ai_prefix,
        )

        # input_data = inputs[prompt_input_key]

        # If the input_data is actually worth storing, we will continue
        worthiness_evaluation = LLMChain(
            llm=self.llm, prompt=self.worthiness_evaluation_prompt
        )
        result = worthiness_evaluation.predict(
            history=buffer_string,
            input=inputs[prompt_input_key],
            human_prefix=self.human_prefix,
        )

        if result.strip() == "WORTHY":
            # Create an LLMChain to see if this data is worth storing:
            entity_extraction = LLMChain(
                llm=self.llm, prompt=self.entity_extraction_prompt
            )
            entities = entity_extraction.predict(
                history=buffer_string,
                input=inputs[prompt_input_key],
                human_prefix=self.human_prefix,
            )

            # Create an LLMChain to summarize the entity:
            # Only summarize for the first entity- no need to do more than one,
            # they will all be the same (entity does not change the summary)
            entity_extraction = LLMChain(
                llm=self.llm, prompt=self.entity_summarization_prompt
            )
            summary = entity_extraction.predict(
                entity=entities.split(",")[0].strip(),
                summary="",
                history=buffer_string,
                input=inputs[prompt_input_key],
                human_prefix=self.human_prefix,
            )

            # We do want to store each entity, however
            for entity in entities.split(","):
                self.entity_store.set(entity.strip(), summary)

    def clear(self) -> None:
        """Clear memory contents."""
        self.chat_memory.clear()
        self.entity_cache.clear()
        self.entity_store.clear()

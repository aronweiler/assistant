from pydantic import Field
import logging
import openai

from typing import Any, Union, Optional

# Add the directory above src to the path
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from langchain.llms.openai import OpenAI
from langchain.memory.entity import BaseEntityStore
from langchain.base_language import BaseLanguageModel
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema.messages import get_buffer_string
from langchain.memory.chat_memory import BaseChatMessageHistory
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory


from src.memory.prompts import (
    ENTITY_SUMMARIZATION_PROMPT,
    RELATED_ENTITY_PROMPT,
    ENTITY_EXTRACTION_PROMPT,
    SUMMARIZATION_PROMPT,
)

from src.memory.entity_store_models import Entity, EntityDetails


class PostgreSQLEntityStore(BaseEntityStore):
    class Config:
        arbitrary_types_allowed = True

    engine: Any = None
    entity_table: Entity = None
    entity_details_table: EntityDetails = None
    Session: Any = None
    chat_memory: Any
    llm: Union[BaseLanguageModel, None] = None
    entity_summarization_prompt: PromptTemplate = ENTITY_SUMMARIZATION_PROMPT
    related_entity_prompt: PromptTemplate = RELATED_ENTITY_PROMPT
    entity_extraction_prompt: PromptTemplate = ENTITY_EXTRACTION_PROMPT
    summarization_prompt: PromptTemplate = SUMMARIZATION_PROMPT
    human_prefix: str = "Human"
    ai_prefix: str = "AI"

    # Number of recent message pairs to consider when updating entities:
    k: int = 3

    def __init__(
        self,
        db_url: str,
        llm: Union[BaseLanguageModel, None] = None,
        entity_summarization_prompt: PromptTemplate = ENTITY_SUMMARIZATION_PROMPT,
        related_entity_prompt: PromptTemplate = RELATED_ENTITY_PROMPT,
        entity_extraction_prompt: PromptTemplate = ENTITY_EXTRACTION_PROMPT,
        summarization_prompt: PromptTemplate = SUMMARIZATION_PROMPT,
        chat_memory: BaseChatMessageHistory = Field(default_factory=ChatMessageHistory),
        human_prefix: str = "Human",
        ai_prefix: str = "AI",
        *args: Any,
        **kwargs: Any,
    ):
        try:
            import sqlalchemy as sa
            from sqlalchemy.orm import sessionmaker
        except ImportError:
            raise ImportError(
                "Could not import sqlalchemy python package. "
                "Please install it with `pip install sqlalchemy`."
            )

        super().__init__(*args, **kwargs)

        self.human_prefix = human_prefix
        self.ai_prefix = ai_prefix
        self.chat_memory = chat_memory
        self.llm = llm
        self.entity_summarization_prompt = entity_summarization_prompt
        self.related_entity_prompt = related_entity_prompt
        self.entity_extraction_prompt = entity_extraction_prompt
        self.summarization_prompt = summarization_prompt

        self.engine = sa.create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

        self.entity_table = Entity()
        self.entity_table.metadata.create_all(self.engine)

        self.entity_details_table = EntityDetails()
        self.entity_details_table.metadata.create_all(self.engine)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        try:
            import sqlalchemy as sa
            from sqlalchemy.orm import joinedload, selectinload
        except ImportError:
            raise ImportError(
                "Could not import sqlalchemy python package. "
                "Please install it with `pip install sqlalchemy`."
            )

        with self.Session() as session:
            # First get from the entity table with it's children
            query = session.query(Entity).filter(Entity.entity_key == key)
            query = query.options(selectinload(Entity.details))

            results = session.execute(query)
            entities = []

            if results is not None:
                # This could get large if I don't limit it
                values_count = 0

                for result in results:
                    for details in result[0].details:
                        values_count += 1
                        entities.append(details.entity_value)

                return entities

            return default

    def set(self, key: str, value: Optional[str]) -> None:
        if not value:
            return self.delete(key)

        new_key = self.exists(key)
        if new_key != None:
            return self.update(new_key, value)

        with self.Session() as session:
            # Only create the entity here, let update handle the rest
            new_entity = Entity(entity_key=key, embedding=self.get_embedding(key))
            session.add(new_entity)
            session.commit()

        return self.update(key, value)

    def update(self, key: str, value: str) -> None:
        try:
            import sqlalchemy as sa
            from sqlalchemy.orm import selectinload
        except ImportError:
            raise ImportError(
                "Could not import sqlalchemy python package. "
                "Please install it with `pip install sqlalchemy`."
            )

        with self.Session() as session:
            # Extract an arbitrary window of the last message pairs from
            # the chat history, where the hyperparameter k is the
            # number of message pairs:
            buffer_string = get_buffer_string(
                self.chat_memory.messages[-self.k * 2 :],
                human_prefix=self.human_prefix,
                ai_prefix=self.ai_prefix,
            )

            # Find the closest 2 entity values that might be related to this one
            # Load the other entities related to the value, as well- we'll use them later
            query = session.query(EntityDetails).options(
                selectinload(EntityDetails.entities)
            )
            neighbors = self.get_nearest_neighbors(
                session,
                query,
                EntityDetails.embedding,
                self.get_embedding(value),
                top_k=2,
            )

            has_neighbors = False
            # Evaluate each neighbor to see if it is worth adding this new value to
            for entity_detail in neighbors:
                has_neighbors = True

                # First see if its an exact match
                if entity_detail.entity_value.lower() == value.lower():
                    # If it is, then we don't need to do anything
                    return

                # If it's not an exact match, see if it is related at all to the closest neighbor.
                # The LLM will do that for us here, and will return "related" if it is, or "unrelated" if it isn't.
                # If it is unrelated, we need to add a new entity detail value
                # If it is related, we should try to combine the two values into one entity detail value
                # We should also make sure that all of the entities are properly linked
                is_related = LLMChain(llm=self.llm, prompt=self.related_entity_prompt)

                related = is_related.predict(
                    summary=entity_detail.entity_value,
                    entity=key,
                    history=buffer_string,
                    input=value,
                    human_prefix=self.human_prefix,
                )

                if related.strip().lower() == "none":
                    logging.debug("No related entities found")
                    continue

                if related.strip().lower() == "related":
                    # it's related, pass it on to the summarization llm
                    summarizer = LLMChain(
                        llm=self.llm, prompt=self.entity_summarization_prompt
                    )

                    summary = summarizer.predict(
                        summary=entity_detail.entity_value,
                        entity=key,
                        history=buffer_string,
                        input=value,
                        human_prefix=self.human_prefix,
                    )

                    # Update the existing entity detail with the new summary
                    entity_detail.entity_value = summary.strip()
                    entity_detail.embedding = self.get_embedding(summary.strip())
                    session.commit()

                else:
                    # it's unrelated, add it to the database as a new entity detail
                    entity_detail = EntityDetails(
                        entity_value=value, embedding=self.get_embedding(value)
                    )
                    session.add(entity_detail)
                    session.commit()

                # Extract entities and link them (if they haven't been linked already)
                self.extract_and_link(session, buffer_string, entity_detail)

            # If we didn't find any neighbors, then we need to add a new entity detail
            if not has_neighbors:
                entity_detail = EntityDetails(
                    entity_value=value, embedding=self.get_embedding(value)
                )
                session.add(entity_detail)
                session.commit()

                # Extract entities and link them (if they haven't been linked already)
                self.extract_and_link(session, buffer_string, entity_detail)

    def extract_and_link(
        self, session, buffer_string: str, entity_detail: EntityDetails
    ):
        from sqlalchemy.orm import selectinload

        # Always try to link all of the related entities (getting the entities in the value from the LLM first)
        extraction = LLMChain(llm=self.llm, prompt=self.entity_extraction_prompt)
        entities = extraction.predict(
            history=buffer_string,
            input=entity_detail.entity_value,
            human_prefix=self.human_prefix,
        )

        # Split the entities into a list
        if entities.strip().lower() != "none":
            entities = entities.split(",")
            for entity_name in entities:
                # Get the entity from the database
                query = session.query(Entity).options(selectinload(Entity.details))
                query = query.filter(Entity.entity_key == entity_name.strip())
                entity = query.first()

                # Link the detail to the entity (if not already)
                if entity is None:
                    # Create a new entity
                    new_entity = Entity(
                        entity_key=entity_name.strip(),
                        embedding=self.get_embedding(entity_name.strip()),
                    )
                    new_entity.details.append(entity_detail)
                    entity_detail.entities.append(new_entity)
                    session.add(new_entity)
                    session.commit()
                elif entity_detail not in entity.details:
                    # Link existing entity
                    entity.details.append(entity_detail)
                    entity_detail.entities.append(entity)
                    session.commit()

    def get_nearest_neighbors(
        self, session, query, item, embedding, top_k=5, distance=0.6
    ):
        v1 = session.scalars(
            query.filter(item.l2_distance(embedding) < distance)
            .order_by(item.l2_distance(embedding))
            .limit(top_k)
        )
        # v2 = session.scalars(query.order_by(EntityDetails.embedding.l2_distance(embedding)).limit(top_k))
        return v1

    def get_embedding(self, text: str, embedding_model="text-embedding-ada-002"):
        return openai.embeddings.create(input=[text], model=embedding_model).data[0].embedding

    def delete(self, key: str) -> None:
        raise NotImplementedError(
            "Delete method not implemented for PostgreSQLEntityStore"
        )

    def exists(self, key: str) -> str:
        try:
            import sqlalchemy as sa
        except ImportError:
            raise ImportError(
                "Could not import sqlalchemy python package. "
                "Please install it with `pip install sqlalchemy`."
            )
        with self.Session() as session:
            query = session.query(Entity)
            # Find only the most similar entity
            # Note: The 0.3 distance is calculated to get the most bang for our buck here.
            # Exact matches are easy, but we want to find the most similar entity that is not an exact match and still is the same entity
            neighbors = self.get_nearest_neighbors(
                session,
                query,
                Entity.embedding,
                self.get_embedding(key),
                top_k=1,
                distance=0.3,
            )
            # result = .filter(Entity.entity_key == key).first()
            for neighbor in neighbors:
                return neighbor.entity_key

            return None
        
    def clean_entity_details(self) -> None:
        try:
            import sqlalchemy as sa
        except ImportError:
            raise ImportError(
                "Could not import sqlalchemy python package. "
                "Please install it with `pip install sqlalchemy`."
            )
        with self.Session() as session:
            query = session.query(EntityDetails).all()
            # Loop through all of the details, and re-summarize to remove duplication within each, and hopefully reduce their size
            for entity_detail in query:
                # Get the summary
                summarizer = LLMChain(llm=self.llm, prompt=self.summarization_prompt)
                summary = summarizer.predict(                    
                    input=entity_detail.entity_value
                )

                # Update the existing entity detail with the new summary
                entity_detail.entity_value = summary.strip()
                entity_detail.embedding = self.get_embedding(summary.strip())
                session.commit()


    def clear(self) -> None:
        raise NotImplementedError(
            "Clear method not implemented for PostgreSQLEntityStore"
        )


# Testing
if __name__ == "__main__":
    from db.models.vector_database import VectorDatabase

    llm = OpenAI(temperature=0)

    connection_string = VectorDatabase.get_connection_string("src/db/database/db.env")
    postgres_entity_store = PostgreSQLEntityStore(
        llm=llm, db_url=connection_string, chat_memory=ChatMessageHistory()
    )

    result = postgres_entity_store.set("Benson", "Benson sleeping on the couch")
    result = postgres_entity_store.set(
        "TestUser", "TestUser is having fun with building the entity store"
    )
    result = postgres_entity_store.set(
        "Jimbob",
        "Jimbob is watching Benson, who is asleep on the couch, and TestUser, who is now watching TV.",
    )

    result = postgres_entity_store.get("TestUser", "sadface")
    print(result)
    result = postgres_entity_store.get("Jimbob", "sadface")
    print(result)
    result = postgres_entity_store.get("Benson", "sadface")
    print(result)

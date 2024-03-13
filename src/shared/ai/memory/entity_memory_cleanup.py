
from langchain.llms.openai import OpenAI
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory

# Add the directory above src to the path
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.shared.ai.memory.postgres_entity_store import PostgreSQLEntityStore
from src.shared.database.models.vector_database import VectorDatabase


# This is a simple utility that kicks off the clean up of the stored entity memory.
# We will loop through the entity details, and re-summarize them to remove duplication.
def clean_entity_details():
    llm = OpenAI(temperature=0)

    connection_string = VectorDatabase.get_connection_string("src/db/database/db.env")
    postgres_entity_store = PostgreSQLEntityStore(
        llm=llm, db_url=connection_string, chat_memory=ChatMessageHistory()
    )

    postgres_entity_store.clean_entity_details()
    

# testing
if __name__ == "__main__":
    clean_entity_details()
    
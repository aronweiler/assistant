import os
import sys
import logging
import json
from typing import Union, List
from uuid import UUID

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from tools.memory.memory_tool_configuration import MemoryToolConfiguration
from db.models.memories import Memories
from db.models.users import Users
from db.models.vector_database import SearchType
from db.database.models import Memory


class MemoryTool:
    def __init__(self, json_args):
        self.configuration = MemoryToolConfiguration(json_args)
        self.memories = Memories(self.configuration.db_env_location)
        self.users = Users(self.configuration.db_env_location)

    # Just wrap the memory call- might want to do other thing here, like pull in their profile info
    def get_user_information(
        self,
        text: str,
        associated_user_email:str,
    ) -> str:
        """Get a user's profile information.  If no associated user is specified, the profile information will be returned regardless of the user it is associated with.  If an associated user is specified, the profile information will only be returned if it is associated with that user.
        
        Args:
            text (str): The text to search for in the memory.
            associated_user_email (str): The email of the user to search for. 
            """
        try:
            with self.users.session_context(self.users.Session()) as session:
                user = self.users.find_user_by_email(session, associated_user_email)
                profile_string = f"User: {user.name} ({user.email}), age: {user.age}, location: {user.location}"

            memories = self._get_memories(
                text=text, associated_user_email=associated_user_email
            )

            return profile_string + "\n" + "\n".join([m.memory_text for m in memories])
        except:
            return """Fail!  Check your input and try again."""

    def get_memory(
        self,
        text: str,
        associated_user_email: Union[str, None] = None,
    ) -> str:
        """Use this tool to retrieve a memory about an interaction you've had, or when a user asks you to remember something.  If no associated user is specified, the memory will be returned regardless of the user it is associated with.  If an associated user is specified, the memory will only be returned if it is associated with that user.
        
        Args:
            text (str): The text to search for in the memory. This field is required!
            associated_user_email (Union[str, None], optional): The email of the user to search for.  Defaults to None.
            """
        try:
            with self.users.session_context(self.users.Session()) as session:
                memories = self.memories.find_memories(
                    session,
                    memory_text_search_query=text,
                    associated_user_email=associated_user_email,
                    eager_load=[Memory.user],
                    search_type=SearchType.similarity,
                    top_k=self.configuration.top_k,
                    distance=0.5,
                )

                memories_output = []
                for memory in memories:
                    memory_string = f"{memory.record_created}:"
                    if memory.user is not None:
                        memory_string += (
                            f" associated_user: {memory.user.name} ({memory.user.email})"
                        )

                    if memory.interaction_id is not None:
                        memory_string += f" interaction_id: '{memory.interaction_id}'"

                    memory_string += f" memory: '{memory.memory_text}'"
                    memories_output.append(memory_string)

            if len(memories_output) > 0:
                return "Found the following memories: " + "\n".join(memories_output)
            else:
                return "No memories found related to that query.  You should query the user for more information."

        except Exception as e:
            return f"Failed to retrieve memories.  Error: {e}"


# Testing
if __name__ == "__main__":
    # Test the tool
    import openai
    from dotenv import dotenv_values, load_dotenv
    load_dotenv()

    openai.api_key = dotenv_values().get("OPENAI_API_KEY")
    
    json_args = {
        "db_env_location": "src/db/database/db.env",
        "top_k": 5}
    
    tool = MemoryTool(json_args)

    print(tool.get_memory("I like to eat pizza", None))
    print(tool.get_memory("I like to eat pizza", "test@test"))
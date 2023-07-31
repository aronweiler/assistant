import logging
import json
from typing import Union, List
from uuid import UUID

from ai.open_ai.tools.memory.memory_tool_configuration import MemoryToolConfiguration
from memory.models.memories import Memories, Memory
from memory.models.users import Users, User
from memory.models.vector_database import SearchType


class MemoryTool:
    def __init__(self, json_args):
        self.configuration = MemoryToolConfiguration(json_args)
        self.memories = Memories(self.configuration.db_env_location)
        self.users = Users(self.configuration.db_env_location)

    # Just wrap the memory call- might want to do other thing here, like pull in their profile info
    def get_user_information(
        self,
        text: str,
        associated_user_email: Union[str, None] = None,
    ) -> str:
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
        try:
            memories = self._get_memories(
                text=text, associated_user_email=associated_user_email
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

        except:
            return """Fail!  Check your input and try again."""

    def _get_memories(self, text: str, associated_user_email: Union[str, None] = None):
        with self.users.session_context(self.users.Session()) as session:
            return self.memories.find_memories(
                session,
                memory_text_search_query=text,
                associated_user_email=associated_user_email,
                eager_load=[Memory.user],
                search_type=SearchType.similarity,
                top_k=self.configuration.top_k,
                distance=0.5,
            )

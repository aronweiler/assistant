from typing import Union, List
from memory.database.models import User, UserSetting
from memory.models.vector_database import VectorDatabase

class ToolsUsed(VectorDatabase):
    def __init__(self, db_env_location):
       super().__init__(db_env_location)

    ### TBD
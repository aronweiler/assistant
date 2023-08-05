from typing import Union, List
from conversation.database.models import User, UserSetting
from conversation.models.vector_database import VectorDatabase

class ToolsUsed(VectorDatabase):
    def __init__(self, db_env_location):
       super().__init__(db_env_location)

    ### TBD
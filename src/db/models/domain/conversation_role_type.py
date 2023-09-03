from enum import Enum

# Role type enum. This needs to be kept in sync with the database
class ConversationRoleType(Enum):
    SYSTEM = 1
    ASSISTANT = 2
    USER = 3
    FUNCTION = 4
    ERROR = 5
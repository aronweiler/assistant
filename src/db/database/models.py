from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Uuid,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    CheckConstraint,
    Boolean,
)

from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

EMBEDDING_DIMENSIONS = 1536

# ModelBase allows us to access the relationships of a model by using the [] operator
class ModelBase(Base): 
    __abstract__ = True  # This makes ModelBase an abstract class, so it won't create a table in the database

    __tablename__ = "none" # This is just a placeholder, it will be overridden by the child class    


class User(ModelBase):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    location = Column(String, nullable=True)
    email = Column(String, nullable=False, unique=True)

    # Define a one-to-many relationship with other tables
    conversations = relationship("Conversation", back_populates="user")
    memories = relationship("Memory", back_populates="user")
    documents = relationship("Document", back_populates="user")
    user_settings = relationship("UserSetting", back_populates="user")
    
    def get_setting(self, setting_name, default):        
        for setting in self.user_settings:
            if setting.setting_name == setting_name:
                return setting.setting_value
            
        return default
    
    def set_setting(self, setting_name, value):        
        for setting in self.user_settings:
            if setting.setting_name == setting_name:
                setting.setting_value = value
    

class UserSetting(ModelBase):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    setting_name = Column(String, nullable=False)
    setting_value = Column(String, nullable=False)

    # Define the ForeignKeyConstraint to ensure the user_id exists in the users table
    user_constraint = ForeignKeyConstraint([user_id], [User.id])

    # Define the CheckConstraint to enforce user_id existing in users table
    user_check_constraint = CheckConstraint(
        "user_id IN (SELECT id FROM users)", name="ck_user_id_in_users"
    )

    # Define the many to one relationship with User
    user = relationship("User", back_populates="user_settings")

# TBD
# class Tool(ModelBase):
#     __tablename__ = "tools"

#     id = Column(Integer, primary_key=True)
#     name = Column(String, nullable=False, unique=True)
#     description = Column(String, nullable=False)
#     tool_module = Column(String, nullable=False)
#     tool_class = Column(String, nullable=False)
#     tool_arguments = Column(String, nullable=True)

#     # Define a one-to-many relationship with ConversationToolUse
#     conversation_tool_uses = relationship("ConversationToolUse", back_populates="tool")

#     _fields_to_relationships = {
#         "conversation_tool_uses": conversation_tool_uses,
#     }

class Conversation(ModelBase):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)
    interaction_id = Column(Uuid, nullable=False)        
    conversation_text = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    is_ai_response = Column(Boolean, nullable=False)
    additional_metadata = Column(String, nullable=True)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    exception = Column(String, nullable=True)

    # flag for deletion
    is_deleted = Column(Boolean, nullable=False, default=False)

    # Define the ForeignKeyConstraint to ensure the user_id exists in the users table
    user_constraint = ForeignKeyConstraint([user_id], [User.id])

    # Define the CheckConstraint to enforce user_id being NULL or existing in users table
    user_check_constraint = CheckConstraint(
        "user_id IS NULL OR user_id IN (SELECT id FROM users)",
        name="ck_user_id_in_users",
    )

    # Define the relationship with User
    user = relationship("User", back_populates="conversations")
    conversation_tool_uses = relationship("ConversationToolUse", back_populates="conversation")    

class ConversationToolUse(ModelBase):
    __tablename__ = "conversation_tool_uses"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    tool_name = Column(String, nullable=False)
    tool_input = Column(String, nullable=False)
    tool_output = Column(String, nullable=False)
    additional_metadata = Column(String, nullable=True)

    # Define the ForeignKeyConstraint to ensure the conversation_id exists in the conversations table
    conversation_constraint = ForeignKeyConstraint([conversation_id], [Conversation.id])

    # Define the CheckConstraint to enforce conversation_id existing in conversations table
    conversation_check_constraint = CheckConstraint(
        "conversation_id IN (SELECT id FROM conversations)",
        name="ck_conversation_id_in_conversations",
    )

    # Define the relationship with Conversation
    conversation = relationship("Conversation", back_populates="conversation_tool_uses")

class Memory(ModelBase):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)
    memory_text = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    interaction_id = Column(Uuid, nullable=True)
    additional_metadata = Column(String, nullable=True)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)

    # Define the ForeignKeyConstraint to ensure the user_id exists in the users table
    user_constraint = ForeignKeyConstraint([user_id], [User.id])

    # Define the CheckConstraint to enforce user_id being NULL or existing in users table
    user_check_constraint = CheckConstraint(
        "user_id IS NULL OR user_id IN (SELECT id FROM users)",
        name="ck_user_id_in_users",
    )

    # Define the CheckConstraint to enforce interaction_id being NULL or existing in conversations table
    conversation_check_constraint = CheckConstraint(
        "interaction_id IS NULL OR interaction_id IN (SELECT interaction_id FROM conversations)",
        name="ck_interaction_id_in_conversations",
    )

    # TODO: If this is a memory about a tool, we need to link to the tool

    # Define the relationship with User
    user = relationship("User", back_populates="memories")

class Document(ModelBase):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)
    document_text = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    additional_metadata = Column(String, nullable=True)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=True)

    # Define the ForeignKeyConstraint to ensure the user_id exists in the users table
    user_constraint = ForeignKeyConstraint([user_id], [User.id])

    # Define the CheckConstraint to enforce user_id being NULL or existing in users table
    user_check_constraint = CheckConstraint(
        "user_id IS NULL OR user_id IN (SELECT id FROM users)",
        name="ck_user_id_in_users",
    )

    # Define the relationship with User
    user = relationship("User", back_populates="documents")

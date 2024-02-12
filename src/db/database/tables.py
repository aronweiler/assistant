# This file contains the SQLAlchemy ORM class definitions for a database schema used in the assistant application.
# Each class within this file represents a distinct table in the database, with attributes corresponding to the table columns.
# The classes also define relationships between tables, such as one-to-many and many-to-many associations,
# which facilitate the querying and manipulation of related data.
# The file is structured to provide a clear mapping between the application's data models and the underlying database structure,
# enabling efficient data storage, retrieval, and management.

from sqlalchemy import (
    Column,
    Integer,
    String,
    Table,
    Uuid,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    CheckConstraint,
    UniqueConstraint,
    Boolean,
    LargeBinary,
)

from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


# ModelBase serves as a base class for all models. It provides common functionality and ensures that
# the derived classes are mapped to tables in the database.
class ModelBase(Base):
    __abstract__ = True  # This makes ModelBase an abstract class, so it won't create a table in the database

    __tablename__ = (
        "none"  # This is just a placeholder, it will be overridden by the child class
    )


# User model represents a user in the system with their associated properties and relationships.
class User(ModelBase):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    location = Column(String, nullable=True)
    email = Column(String, nullable=False, unique=True)

    # Define a one-to-many relationship with other tables
    conversation_messages = relationship("ConversationMessage", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    files = relationship("File", back_populates="user")
    documents = relationship("Document", back_populates="user")


# TODO: Refactor Jarvis so that all of the settings are contained within this table.
# Need to do this before it can become multi-user
class UserSetting(ModelBase):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    setting_name = Column(String, nullable=False)
    setting_value = Column(String, nullable=False)
    available_for_llm = Column(Boolean, nullable=False, default=False)

    # Define the ForeignKeyConstraint to ensure the user_id exists in the users table
    user_constraint = ForeignKeyConstraint([user_id], [User.id])

    # Define the CheckConstraint to enforce user_id existing in users table
    user_check_constraint = CheckConstraint(
        "user_id IN (SELECT id FROM users)", name="ck_user_id_in_users"
    )


# Conversation model represents a conversation in the system with its properties and relationships.
class Conversation(ModelBase):
    __tablename__ = "conversations"

    id = Column(Uuid, primary_key=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)
    conversation_summary = Column(String, nullable=False)
    needs_summary = Column(Boolean, nullable=False, default=True)
    last_selected_collection_id = Column(Integer, nullable=False, default=-1)
    last_selected_code_repo = Column(Integer, nullable=False, default=-1)
    user_id = Column(Integer, ForeignKey("users.id"))
    is_deleted = Column(Boolean, nullable=False, default=False)

    conversation_messages = relationship(
        "ConversationMessage", back_populates="conversation"
    )

    # Define the ForeignKeyConstraint to ensure the user_id exists in the users table
    user_constraint = ForeignKeyConstraint([user_id], ["users.id"])

    # Define the CheckConstraint to enforce user_id being NULL or existing in users table
    user_check_constraint = CheckConstraint(
        "user_id IS NULL OR user_id IN (SELECT id FROM users)",
        name="ck_user_id_in_users",
    )

    # Define the relationship with User and Conversation
    user = relationship("User", back_populates="conversations")
    tool_call_results = relationship("ToolCallResults", back_populates="conversation")


# ConversationMessage model represents a message within a conversation, including its properties and relationships.
class ConversationMessage(ModelBase):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)
    conversation_id = Column(Uuid, ForeignKey("conversations.id"), nullable=False)
    conversation_role_type_id = Column(
        Integer, ForeignKey("conversation_role_types.id")
    )
    message_text = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    additional_metadata = Column(String, nullable=True)
    # embedding = Column(Vector(dim=None), nullable=True)
    # embedding_model_name = Column(String, nullable=False)
    exception = Column(String, nullable=True)

    # flag for deletion
    is_deleted = Column(Boolean, nullable=False, default=False)

    # Define the ForeignKeyConstraint to ensure the user_id exists in the users table
    user_constraint = ForeignKeyConstraint([user_id], ["users.id"])

    # Define the ForeignKeyConstraint to ensure the conversation_role_type_id exists in the conversation_role_types table
    conversation_role_type_constraint = ForeignKeyConstraint(
        [conversation_role_type_id], ["conversation_role_types.id"]
    )

    # Define the CheckConstraint to enforce user_id being NULL or existing in users table
    user_check_constraint = CheckConstraint(
        "user_id IS NULL OR user_id IN (SELECT id FROM users)",
        name="ck_user_id_in_users",
    )

    # Define the foreign key constraint to ensure the conversation_id exists in the conversations table
    conversation_constraint = ForeignKeyConstraint(
        [conversation_id], ["conversations.id"]
    )

    # Define the CheckConstraint to enforce conversation_id existing in conversation_messages table
    conversation_check_constraint = CheckConstraint(
        "conversation_id IN (SELECT id FROM conversations)",
        name="ck_conversation_id_in_conversations",
    )

    # Define the relationship with User
    user = relationship("User", back_populates="conversation_messages")
    conversation = relationship("Conversation", back_populates="conversation_messages")
    conversation_role_type = relationship(
        "ConversationRoleType", back_populates="conversation_messages"
    )


# ConversationRoleType model represents the role types that can be assigned to messages within a conversation.
class ConversationRoleType(ModelBase):
    __tablename__ = "conversation_role_types"

    id = Column(Integer, primary_key=True)
    role_type = Column(String, nullable=False)

    conversation_messages = relationship(
        "ConversationMessage", back_populates="conversation_role_type"
    )


# File model represents a file within the system, including its properties and relationships to other models.
class File(ModelBase):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True)
    collection_id = Column(
        Integer, ForeignKey("document_collections.id"), nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String, nullable=False)
    file_classification = Column(String, nullable=True)
    file_summary = Column(String, nullable=True)
    file_hash = Column(String, nullable=False)
    chunk_size = Column(Integer, nullable=False)
    chunk_overlap = Column(Integer, nullable=False)
    document_count = Column(Integer, nullable=False, default=0)
    file_data = Column(LargeBinary, nullable=False)
    record_created = Column(DateTime, nullable=False, default=datetime.now)

    # Define the ForeignKeyConstraint to ensure the user_id exists in the users table
    user_constraint = ForeignKeyConstraint([user_id], [User.id])

    # Define the CheckConstraint to enforce user_id being NULL or existing in users table
    user_check_constraint = CheckConstraint(
        "user_id IS NULL OR user_id IN (SELECT id FROM users)",
        name="ck_user_id_in_users",
    )

    # Define the relationship with User
    user = relationship("User", back_populates="files")

    # Define the ForeignKeyConstraint to ensure the collection_id exists in the document_collections table
    collection_constraint = ForeignKeyConstraint(
        [collection_id], ["document_collections.id"]
    )

    # Define the CheckConstraint to enforce collection_id existing in document_collections table
    collection_check_constraint = CheckConstraint(
        "collection_id IN (SELECT id FROM document_collections)",
        name="ck_collection_id_in_document_collections",
    )

    # Define the relationship with DocumentCollection
    collection = relationship("DocumentCollection", back_populates="files")

    # Define the relationship with Document
    documents = relationship("Document", back_populates="file")

    __table_args__ = (UniqueConstraint("collection_id", "file_name"),)


# Document model represents a document within the system, detailing its properties and relationships.
class Document(ModelBase):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    collection_id = Column(
        Integer, ForeignKey("document_collections.id"), nullable=False
    )
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    additional_metadata = Column(String, nullable=True)
    document_text = Column(String, nullable=False)
    document_name = Column(String, nullable=False)
    document_text_summary = Column(String, nullable=True)
    document_text_summary_embedding = Column(Vector(dim=None), nullable=True)
    document_text_has_summary = Column(Boolean, nullable=False, default=False)
    embedding = Column(Vector(dim=None), nullable=True)
    question_1 = Column(String, nullable=True)
    embedding_question_1 = Column(Vector(dim=None), nullable=True)
    question_2 = Column(String, nullable=True)
    embedding_question_2 = Column(Vector(dim=None), nullable=True)
    question_3 = Column(String, nullable=True)
    embedding_question_3 = Column(Vector(dim=None), nullable=True)
    question_4 = Column(String, nullable=True)
    embedding_question_4 = Column(Vector(dim=None), nullable=True)
    question_5 = Column(String, nullable=True)
    embedding_question_5 = Column(Vector(dim=None), nullable=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)
    embedding_model_name = Column(String, nullable=False)

    # Define user and collection constraints
    # Define the ForeignKeyConstraint to ensure the user_id exists in the users table
    user_constraint = ForeignKeyConstraint([user_id], [User.id])

    # Define the CheckConstraint to enforce user_id being NULL or existing in users table
    user_check_constraint = CheckConstraint(
        "user_id IS NULL OR user_id IN (SELECT id FROM users)",
        name="ck_user_id_in_users",
    )

    # Define the relationship with User
    user = relationship("User", back_populates="documents")

    # Define the ForeignKeyConstraint to ensure the collection_id exists in the document_collections table
    collection_constraint = ForeignKeyConstraint(
        [collection_id], ["document_collections.id"]
    )

    # Define the CheckConstraint to enforce collection_id existing in document_collections table
    collection_check_constraint = CheckConstraint(
        "collection_id IN (SELECT id FROM document_collections)",
        name="ck_collection_id_in_document_collections",
    )

    # Define the relationship with DocumentCollection
    collection = relationship("DocumentCollection", back_populates="documents")

    # Define the ForeignKeyConstraint to ensure the file_id exists in the files table
    file_constraint = ForeignKeyConstraint([file_id], ["files.id"])

    # Define the CheckConstraint to enforce file_id existing in files table
    file_check_constraint = CheckConstraint(
        "file_id IN (SELECT id FROM files)",
        name="ck_file_id_in_files",
    )

    # Define the relationship with files
    file = relationship("File", back_populates="documents")


# DocumentCollection model represents a collection of documents, including its properties and relationships.
class DocumentCollection(ModelBase):
    __tablename__ = "document_collections"

    id = Column(Integer, primary_key=True)
    collection_name = Column(String, nullable=False, unique=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)
    embedding_name = Column(String, nullable=False)

    documents = relationship("Document", back_populates="collection")

    files = relationship("File", back_populates="collection")


# Association table for the many-to-many relationship between code repositories and code files.
code_repository_files_association = Table(
    "code_repository_files",
    ModelBase.metadata,
    Column(
        "code_repository_id",
        Integer,
        ForeignKey("code_repositories.id"),
        primary_key=True,
    ),
    Column("code_file_id", Integer, ForeignKey("code_files.id"), primary_key=True),
)


# CodeRepository model represents a code repository, including its properties and relationships.
class CodeRepository(ModelBase):
    __tablename__ = "code_repositories"

    id = Column(Integer, primary_key=True)
    code_repository_address = Column(String, nullable=False)
    branch_name = Column(String, nullable=False)
    last_scanned = Column(DateTime, nullable=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)

    # Create a unique constraint on the code_repository_address and branch_name
    __table_args__ = (UniqueConstraint("code_repository_address", "branch_name"),)

    # Update the relationship to use the association table
    code_files = relationship(
        "CodeFile",
        secondary=code_repository_files_association,
        back_populates="code_repositories",
    )


# CodeFile model represents a file within a code repository, detailing its properties and relationships.
class CodeFile(ModelBase):
    __tablename__ = "code_files"

    id = Column(Integer, primary_key=True)
    code_file_name = Column(String, nullable=False)
    code_file_sha = Column(String, nullable=False)
    code_file_content = Column(String, nullable=False)
    code_file_summary = Column(String, nullable=False)

    code_file_summary_embedding = Column(Vector(dim=None), nullable=True)

    record_created = Column(DateTime, nullable=False, default=datetime.now)

    # Update the relationship to use the association table
    code_repositories = relationship(
        "CodeRepository",
        secondary=code_repository_files_association,
        back_populates="code_files",
    )


class CodeFileDependencies(Base):
    __tablename__ = "code_file_dependencies"
    id = Column(Integer, primary_key=True)
    code_file_id = Column(Integer, ForeignKey("code_files.id"))
    dependency_name = Column(String, nullable=False)

    # Establish a relationship with the CodeFile table
    code_file = relationship("CodeFile", back_populates="dependencies")


CodeFile.dependencies = relationship(
    "CodeFileDependencies", order_by=CodeFileDependencies.id, back_populates="code_file"
)


# CodeKeyword model represents a keyword associated with a code file.
class CodeKeyword(ModelBase):
    __tablename__ = "code_keywords"

    id = Column(Integer, primary_key=True)
    code_file_id = Column(Integer, ForeignKey("code_files.id"), nullable=False)
    keyword = Column(String, nullable=False)

    # Relationship to associate keywords with a specific code file.
    code_file = relationship("CodeFile", back_populates="code_keywords")


CodeFile.code_keywords = relationship(
    "CodeKeyword", order_by=CodeKeyword.id, back_populates="code_file"
)


# CodeDescription model represents a description of a code file, including its properties and relationships.
class CodeDescription(ModelBase):
    __tablename__ = "code_descriptions"

    id = Column(Integer, primary_key=True)
    code_file_id = Column(Integer, ForeignKey("code_files.id"), nullable=False)
    description_text = Column(String, nullable=False)
    description_text_embedding = Column(Vector(dim=None), nullable=True)

    # Relationship to associate descriptions with a specific code file.
    code_file = relationship("CodeFile", back_populates="code_descriptions")


CodeFile.code_descriptions = relationship(
    "CodeDescription", order_by=CodeDescription.id, back_populates="code_file"
)


class ToolCallResults(ModelBase):
    __tablename__ = "tool_call_results"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Uuid, ForeignKey("conversations.id"), nullable=False)
    tool_name = Column(String, nullable=False)
    tool_arguments = Column(String, nullable=True)
    tool_results = Column(String, nullable=True)
    include_in_conversation = Column(Boolean, nullable=False, default=False)
    record_created = Column(DateTime, nullable=False, default=datetime.now)

    # Define the relationship with Conversation
    conversation = relationship("Conversation", back_populates="tool_call_results")


Conversation.tool_call_results = relationship(
    "ToolCallResults", order_by=ToolCallResults.id, back_populates="conversation"
)


class SupportedSourceControlProvider(ModelBase):
    __tablename__ = "supported_source_control_providers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class SourceControlProvider(ModelBase):
    __tablename__ = "source_control_providers"

    id = Column(Integer, primary_key=True)
    supported_source_control_provider_id = Column(
        Integer, ForeignKey("supported_source_control_providers.id"), nullable=False
    )
    source_control_provider_name = Column(String, nullable=False, unique=True)
    source_control_provider_url = Column(String, nullable=False)
    requires_authentication = Column(Boolean, nullable=False)
    source_control_access_token = Column(String, nullable=True)
    last_modified = Column(DateTime, nullable=False, default=datetime.now)

    supported_source_control_provider = relationship(
        "SupportedSourceControlProvider", back_populates="source_control_providers"
    )


SupportedSourceControlProvider.source_control_providers = relationship(
    "SourceControlProvider",
    order_by=SourceControlProvider.id,
    back_populates="supported_source_control_provider",
)

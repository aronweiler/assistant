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


# ModelBase allows us to access the relationships of a model by using the [] operator
class ModelBase(Base):
    __abstract__ = True  # This makes ModelBase an abstract class, so it won't create a table in the database

    __tablename__ = (
        "none"  # This is just a placeholder, it will be overridden by the child class
    )


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

    # TODO: Pull this back in when we refactor Jarvis to use this table
    # user_settings = relationship("UserSetting", back_populates="user")

    def get_setting(self, setting_name, default):
        for setting in self.user_settings:
            if setting.setting_name == setting_name:
                return setting.setting_value

        return default

    def set_setting(self, setting_name, value):
        for setting in self.user_settings:
            if setting.setting_name == setting_name:
                setting.setting_value = value


# TODO: Refactor Jarvis so that all of the settings are contained within this table.
# Need to do this before it can become multi-user
# class UserSetting(ModelBase):
#     __tablename__ = "user_settings"

#     id = Column(Integer, primary_key=True)
#     user_id = Column(Integer, ForeignKey("users.id"))
#     setting_name = Column(String, nullable=False)
#     setting_value = Column(String, nullable=False)

#     # Define the ForeignKeyConstraint to ensure the user_id exists in the users table
#     user_constraint = ForeignKeyConstraint([user_id], [User.id])

#     # Define the CheckConstraint to enforce user_id existing in users table
#     user_check_constraint = CheckConstraint(
#         "user_id IN (SELECT id FROM users)", name="ck_user_id_in_users"
#     )

#     # Define the many to one relationship with User
#     user = relationship("User", back_populates="user_settings")


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


class ConversationRoleType(ModelBase):
    __tablename__ = "conversation_role_types"

    id = Column(Integer, primary_key=True)
    role_type = Column(String, nullable=False)

    conversation_messages = relationship(
        "ConversationMessage", back_populates="conversation_role_type"
    )


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


class DocumentCollection(ModelBase):
    __tablename__ = "document_collections"

    id = Column(Integer, primary_key=True)
    collection_name = Column(String, nullable=False, unique=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)
    collection_type = Column(String, nullable=False)

    documents = relationship("Document", back_populates="collection")

    files = relationship("File", back_populates="collection")


# Association table for the many-to-many relationship
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

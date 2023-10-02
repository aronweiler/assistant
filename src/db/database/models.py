from sqlalchemy import (
    Column,
    Integer,
    String,
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

# Note: this is the OpenAI Embedding size
EMBEDDING_DIMENSIONS = 1536


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
    conversations = relationship("Conversation", back_populates="user")
    interactions = relationship("Interaction", back_populates="user")
    files = relationship("File", back_populates="user")
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

class Interaction(ModelBase):
    __tablename__ = "interactions"

    id = Column(Uuid, primary_key=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)
    interaction_summary = Column(String, nullable=False)
    needs_summary = Column(Boolean, nullable=False, default=True)
    last_selected_collection_id = Column(Integer, nullable=False, default=-1)
    user_id = Column(Integer, ForeignKey("users.id"))
    is_deleted = Column(Boolean, nullable=False, default=False)

    conversations = relationship("Conversation", back_populates="interaction")

     # Define the ForeignKeyConstraint to ensure the user_id exists in the users table
    user_constraint = ForeignKeyConstraint([user_id], ["users.id"])
    
    # Define the CheckConstraint to enforce user_id being NULL or existing in users table
    user_check_constraint = CheckConstraint(
        "user_id IS NULL OR user_id IN (SELECT id FROM users)",
        name="ck_user_id_in_users",
    )
    
    # Define the relationship with User and Conversation
    user = relationship("User", back_populates="interactions")    


class Conversation(ModelBase):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)
    interaction_id = Column(Uuid, ForeignKey("interactions.id"), nullable=False)
    conversation_role_type_id = Column(
        Integer, ForeignKey("conversation_role_types.id")
    )
    conversation_text = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    additional_metadata = Column(String, nullable=True)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
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

    # Define the foreign key constraint to ensure the interaction_id exists in the interactions table
    interaction_constraint = ForeignKeyConstraint([interaction_id], ["interactions.id"])

    # Define the CheckConstraint to enforce interaction_id existing in conversations table
    conversation_check_constraint = CheckConstraint(
        "interaction_id IN (SELECT id FROM interactions)",
        name="ck_interaction_id_in_interactions",
    )

    # Define the relationship with User
    user = relationship("User", back_populates="conversations")
    interaction = relationship("Interaction", back_populates="conversations")
    conversation_role_type = relationship(
        "ConversationRoleType", back_populates="conversations"
    )

class ConversationRoleType(ModelBase):
    __tablename__ = "conversation_role_types"

    id = Column(Integer, primary_key=True)
    role_type = Column(String, nullable=False)

    conversations = relationship(
        "Conversation", back_populates="conversation_role_type"
    )

class File(ModelBase):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True)
    collection_id = Column(Integer, ForeignKey("document_collections.id"), nullable=False)        
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String, nullable=False)
    file_classification = Column(String, nullable=True)
    file_summary = Column(String, nullable=True)
    file_hash = Column(String, nullable=False)
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
    collection_constraint = ForeignKeyConstraint([collection_id], ["document_collections.id"])

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
    collection_id = Column(Integer, ForeignKey("document_collections.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    additional_metadata = Column(String, nullable=True)
    document_text = Column(String, nullable=False)
    document_name = Column(String, nullable=False)
    document_text_summary = Column(String, nullable=True)
    document_text_summary_embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)

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
    collection_constraint = ForeignKeyConstraint([collection_id], ["document_collections.id"])

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
    
    documents = relationship("Document", back_populates="collection")

    files = relationship("File", back_populates="collection")

class Project(ModelBase):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    project_name = Column(String, nullable=False, unique=True)
    record_created = Column(DateTime, nullable=False, default=datetime.now)    
    
class DesignDecisions(ModelBase):
    __tablename__ = "design_decisions"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    component = Column(String)
    decision = Column(String, nullable=False)
    details = Column(String, nullable=False)

    project = relationship("Project", backref="design_decisions")

class UserNeeds(ModelBase):
    __tablename__ = "user_needs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    category = Column(String)
    text = Column(String, nullable=False)

    project = relationship("Project", backref="user_needs")


class Requirements(ModelBase):
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    user_need_id = Column(Integer, ForeignKey('user_needs.id'), nullable=False)
    category = Column(String)
    text = Column(String, nullable=False)

    project = relationship("Project", backref="requirements")
    user_need = relationship("UserNeeds", backref="requirements")


class AdditionalDesignInputs(ModelBase):
    __tablename__ = "additional_design_inputs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    requirement_id = Column(Integer, ForeignKey('requirements.id'), nullable=False)
    file_id = Column(Integer, ForeignKey('files.id'), nullable=False)
    description = Column(String, nullable=False)

    project = relationship("Project", backref="additional_design_inputs")
    requirements = relationship("Requirements", backref="additional_design_inputs")
    file = relationship("File", backref="additional_design_inputs")

class Component(Base):
    __tablename__ = "components"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    name = Column(String, nullable=False)
    purpose = Column(String, nullable=False)
    
class ComponentDataHandling(Base):
    __tablename__ = "component_data_handling"

    id = Column(Integer, primary_key=True)
    component_id = Column(Integer, ForeignKey('components.id', ondelete="CASCADE"), nullable=False)
    data_name = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
   
class ComponentInteraction(Base):
    __tablename__ = "component_interactions"

    id = Column(Integer, primary_key=True)
    component_id = Column(Integer, ForeignKey('components.id', ondelete="CASCADE"), nullable=False)
    interacts_with = Column(String, nullable=False)
    description = Column(String, nullable=False)

class ComponentDependency(Base):
    __tablename__ = "component_dependencies"

    id = Column(Integer, primary_key=True)
    component_id = Column(Integer, ForeignKey('components.id', ondelete="CASCADE"), nullable=False)
    dependency_name = Column(String, nullable=False)
    description = Column(String, nullable=False)

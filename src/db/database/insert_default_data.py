# Add the root path to the python path so we can import the database
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from db.models.vector_database import VectorDatabase
from db.database.models import ConversationRoleType, User

db_env = "src/db/database/db.env"

def insert_conversation_role_types():
    vector_db = VectorDatabase(db_env)

    with vector_db.session_context(vector_db.Session()) as session:
        session.add(ConversationRoleType(role_type="system"))
        session.add(ConversationRoleType(role_type="assistant"))
        session.add(ConversationRoleType(role_type="user"))
        session.add(ConversationRoleType(role_type="function"))
        session.add(ConversationRoleType(role_type="error"))
        session.commit()

def insert_users():
    vector_db = VectorDatabase(db_env)

    with vector_db.session_context(vector_db.Session()) as session:
        session.add(User(name="Aron Weiler", email="aronweiler@gmail.com"))
        session.commit()

if __name__ == "__main__":
    insert_conversation_role_types()
    insert_users()
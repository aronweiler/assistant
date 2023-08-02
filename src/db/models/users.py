# For testing
# Add the root path to the python path so we can import the database
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from typing import Union, List, Any
from sqlalchemy.orm.attributes import InstrumentedAttribute
from db.models.vector_database import SearchType, VectorDatabase
from db.database.models import User


class Users(VectorDatabase):
    def __init__(self, db_env_location):
        super().__init__(db_env_location)

    # def find_user_by_name(self, name, eager_load: List[str]) -> Union[User, None]:
    #     query = session.query(User).filter(User.name == name)

    #     query = super().eager_load(query, eager_load)

    #     # If we have more than one user with this name, there's a problem
    #     if query.count() > 1:
    #         raise ValueError(f"More than one user with name {name} found.")

    #     return query.first()
        
    def find_user_by_email(self, session, email, eager_load = []) -> Union[User, None]:
        query = session.query(User).filter(User.email == email)

        query = super().eager_load(query, eager_load)

        return query.first()

    # def find_user_by_id(self, id, eager_load: List[str]) -> Union[User, None]:
    #     query = session.query(User).filter(User.id == id)

    #     query = super().eager_load(query, eager_load)

    #     return query.first()

    def add_update_user(self, session, user: User, eager_load) -> User:        
        query = session.query(User).filter(User.email == user.email)
        query = super().eager_load(query, eager_load)

        temp_user = query.first()

        if temp_user is not None:
            temp_user.name = user.name
            temp_user.age = user.age
            temp_user.location = user.location
            temp_user.email = user.email
            user = temp_user
        else:            
            session.add(user)

        return user

    def get_all_users(self, session, eager_load: List[InstrumentedAttribute[Any]] = []) -> List[User]:
        query = session.query(User)

        query = super().eager_load(query, eager_load)

        return query.all()


if __name__ == "__main__":    

    db_env = "src/memory/long_term/db.env"
    users = Users(db_env)

    with users.session_context(users.Session()) as session:
        user = users.find_user_by_email(session, "gaiaweiler@gmail.com", eager_load=[User.memories, User.conversations, User.user_settings])

        if user is not None:
            for result in user.user_settings:
                print(f"Setting -- User: {result.user.name} - {result.setting_name}={result.setting_value}")

            for result in user.memories:
                print(f"Memory -- User: {result.user.name} - {result.memory_text}")

            for result in user.conversations:
                print(f"Conversation -- User: {result.user.name} - {result.conversation_text}")

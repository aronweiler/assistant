from typing import Union
from src.db.models.vector_database import VectorDatabase
from src.db.database.models import User
from src.db.models.domain.user_model import UserModel


class Users(VectorDatabase):
    
    def get_user_by_email(self, email, eager_load=[]) -> UserModel:
        with self.session_context(self.Session()) as session:
            query = session.query(User).filter(User.email == email)

            query = super().eager_load(query, eager_load)

            return UserModel.from_database_model(query.first())

    def create_user(self, email, name, location, age):
        if self.get_user_by_email(email):
            raise Exception(f"User with email {email} already exists")

        with self.session_context(self.Session()) as session:            
            user = User(email=email, name=name, location=location, age=age)
            session.add(user)
            session.commit()

            return UserModel.from_database_model(user)
from typing import Union
from src.shared.database.models.vector_database import VectorDatabase
from src.shared.database.schema.tables import User
from src.shared.database.models.domain.user_model import UserModel


class Users(VectorDatabase):
    def get_user_by_email(self, email) -> UserModel:
        with self.session_context(self.Session()) as session:
            query = session.query(
                User.id,
                User.name,
                User.age,
                User.location,
                User.email
            ).filter(User.email == email)

            return UserModel.from_database_model(query.first())

    def create_user(self, email, name, location, age):
        if self.get_user_by_email(email):
            raise Exception(f"User with email {email} already exists")

        with self.session_context(self.Session()) as session:
            user = User(email=email, name=name, location=location, age=age)
            session.add(user)
            session.commit()

            return UserModel.from_database_model(user)

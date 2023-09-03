from typing import Union
from db.models.vector_database import VectorDatabase
from db.database.models import User
from db.models.domain.user_model import UserModel


class Users(VectorDatabase):
    def __init__(self, db_env_location):
        super().__init__(db_env_location)

    def get_user_by_email(self, email, eager_load=[]) -> UserModel:
        with self.session_context(self.Session()) as session:
            query = session.query(User).filter(User.email == email)

            query = super().eager_load(query, eager_load)

            return UserModel.from_database_model(query.first())

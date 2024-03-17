from datetime import datetime
from typing import Union
import uuid
from src.shared.database.models.vector_database import VectorDatabase
from src.shared.database.schema.tables import User
from src.shared.database.models.domain.user_model import UserModel


class Users(VectorDatabase):
    def get_all_users(self) -> list[UserModel]:
        with self.session_context(self.Session()) as session:
            query = session.query(
                User.id,
                User.name,
                User.age,
                User.location,
                User.email,
                User.password_hash,
                User.session_id,
                User.session_created,
                User.is_admin,
                User.enabled,
            )
            return [UserModel.from_database_model(user) for user in query.all()]

    def get_user_by_email(self, email) -> UserModel:
        with self.session_context(self.Session()) as session:
            query = session.query(
                User.id,
                User.name,
                User.age,
                User.location,
                User.email,
                User.password_hash,
                User.session_id,
                User.session_created,
                User.is_admin,
                User.enabled,
            ).filter(User.email == email)

            return UserModel.from_database_model(query.first())

    def get_user_by_session_id(self, session_id) -> Union[UserModel, None]:
        with self.session_context(self.Session()) as session:
            query = session.query(
                User.id,
                User.name,
                User.age,
                User.location,
                User.email,
                User.password_hash,
                User.session_id,
                User.session_created,
                User.is_admin,
                User.enabled,
            ).filter(User.session_id == session_id)

            return UserModel.from_database_model(query.first())

    def create_session(self, user_id):
        with self.session_context(self.Session()) as session:
            user = session.query(User).filter(User.id == user_id).first()
            # Create a new GUID for the session
            user.session_id = str(uuid.uuid4())
            user.session_created = datetime.now()
            session.commit()

            return user.session_id

    def update_user_session(self, user_id, session_id):
        with self.session_context(self.Session()) as session:
            user = session.query(User).filter(User.id == user_id).first()
            user.session_id = session_id
            user.session_created = datetime.now()
            session.commit()

    def clear_user_session(self, user_id):
        with self.session_context(self.Session()) as session:
            user = session.query(User).filter(User.id == user_id).first()
            user.session_id = None
            user.session_created = None
            session.commit()

    def create_user(
        self, email, name, location, age, password_hash, is_admin=False, enabled=True
    ):
        if self.get_user_by_email(email):
            raise Exception(f"User with email {email} already exists")

        with self.session_context(self.Session()) as session:
            user = User(
                email=email,
                name=name,
                location=location,
                age=age,
                password_hash=password_hash,
                is_admin=is_admin,
                enabled=enabled,
            )
            session.add(user)
            session.commit()

            return UserModel.from_database_model(user)

    def update_user(self, user_model: UserModel):
        with self.session_context(self.Session()) as session:
            user = session.query(User).filter(User.id == user_model.id).first()
            user.name = user_model.name
            user.age = user_model.age
            user.location = user_model.location
            user.email = user_model.email

            if user_model.password_hash:
                user.password_hash = user_model.password_hash

            user.is_admin = user_model.is_admin
            user.enabled = user_model.enabled
            session.commit()

            return UserModel.from_database_model(user)

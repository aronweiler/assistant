from src.shared.database.schema.tables import User


class UserModel:
    def __init__(self, id, name, age, location, email, password_hash, session_id, session_created):
        self.id = id
        self.name = name
        self.age = age
        self.location = location
        self.email = email
        self.password_hash = password_hash
        self.session_id = session_id
        self.session_created = session_created

    def to_database_model(self):
        return User(
            id=self.id,
            name=self.name,
            age=self.age,
            location=self.location,
            email=self.email,
            password_hash=self.password_hash,
            session_id=self.session_id,
            session_created=self.session_created
        )

    @classmethod
    def from_database_model(cls, db_user):
        if db_user is None:
            return None

        return cls(
            id=db_user.id,
            name=db_user.name,
            age=db_user.age,
            location=db_user.location,
            email=db_user.email,
            password_hash=db_user.password_hash,
            session_id=db_user.session_id,
            session_created=db_user.session_created
        )

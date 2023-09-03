from db.database.models import User

class UserModel:
    def __init__(self, id, name, age, location, email, conversations=None, interactions=None,
                 files=None, documents=None, user_settings=None):
        self.id = id
        self.name = name
        self.age = age
        self.location = location
        self.email = email
        self.conversations = conversations or []
        self.interactions = interactions or []
        self.files = files or []
        self.documents = documents or []
        self.user_settings = user_settings or []

    def get_setting(self, setting_name, default):
        for setting in self.user_settings:
            if setting.setting_name == setting_name:
                return setting.setting_value
        return default

    def set_setting(self, setting_name, value):
        for setting in self.user_settings:
            if setting.setting_name == setting_name:
                setting.setting_value = value

    def to_database_model(self):
        return User(
            id=self.id,
            name=self.name,
            age=self.age,
            location=self.location,
            email=self.email,
            conversations=self.conversations,
            interactions=self.interactions,
            files=self.files,
            documents=self.documents,
            user_settings=self.user_settings
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
            conversations=db_user.conversations,
            interactions=db_user.interactions,
            files=db_user.files,
            documents=db_user.documents,
            user_settings=db_user.user_settings
        )

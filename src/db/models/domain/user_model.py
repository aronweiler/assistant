from src.db.database.models import User


class UserModel:
    def __init__(self, id, name, age, location, email):
        self.id = id
        self.name = name
        self.age = age
        self.location = location
        self.email = email

    # def get_setting(self, setting_name, default):
    #     for setting in self.user_settings:
    #         if setting.setting_name == setting_name:
    #             return setting.setting_value
    #     return default

    # def set_setting(self, setting_name, value):
    #     for setting in self.user_settings:
    #         if setting.setting_name == setting_name:
    #             setting.setting_value = value

    def to_database_model(self):
        return User(
            id=self.id,
            name=self.name,
            age=self.age,
            location=self.location,
            email=self.email
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
        )

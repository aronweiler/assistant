from db.database.models import UserSetting

class UserSettingModel:
    def __init__(self, id, user_id, setting_name, setting_value, user=None):
        self.id = id
        self.user_id = user_id
        self.setting_name = setting_name
        self.setting_value = setting_value
        self.user = user

    def to_database_model(self):
        return UserSetting(
            id=self.id,
            user_id=self.user_id,
            setting_name=self.setting_name,
            setting_value=self.setting_value,
            user=self.user
        )

    @classmethod
    def from_database_model(cls, db_user_setting):
        return cls(
            id=db_user_setting.id,
            user_id=db_user_setting.user_id,
            setting_name=db_user_setting.setting_name,
            setting_value=db_user_setting.setting_value,
            user=db_user_setting.user
        )

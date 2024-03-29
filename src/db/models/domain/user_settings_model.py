from src.db.database.tables import UserSetting


class UserSettingModel:
    def __init__(self, user_id, setting_name, setting_value, available_for_llm):
        self.user_id = user_id
        self.setting_name = setting_name
        self.setting_value = setting_value
        self.available_for_llm = available_for_llm

    @staticmethod
    def to_database_model(user_setting):
        return UserSetting(
            user_id=user_setting.user_id,
            setting_name=user_setting.setting_name,
            setting_value=user_setting.setting_value,
            available_for_llm=user_setting.available_for_llm,
        )

    @staticmethod
    def from_database_model(db_model):
        return UserSettingModel(
            user_id=db_model.user_id,
            setting_name=db_model.setting_name,
            setting_value=db_model.setting_value,
            available_for_llm=db_model.available_for_llm,
        )

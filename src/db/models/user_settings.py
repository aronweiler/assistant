from src.db.database.tables import UserSetting
from src.db.models.domain.user_settings_model import UserSettingModel
from src.db.models.vector_database import VectorDatabase


class UserSettings(VectorDatabase):

    def get_user_settings(self, user_id, available_for_llm=False):
        with self.session_context(self.Session()) as session:
            db_models = (
                session.query(UserSetting)
                .filter(
                    UserSetting.user_id == user_id,
                    UserSetting.available_for_llm == available_for_llm,
                )
                .all()
            )
            return [
                UserSettingModel.from_database_model(db_model) for db_model in db_models
            ]

    def get_user_setting(
        self, user_id, setting_name, default_value=None, available_for_llm=False
    ):
        with self.session_context(self.Session()) as session:
            db_model = (
                session.query(UserSetting)
                .filter(
                    UserSetting.user_id == user_id,
                    UserSetting.setting_name == setting_name,
                    UserSetting.available_for_llm == available_for_llm,
                )
                .first()
            )

            if db_model:
                return UserSettingModel.from_database_model(db_model)
            elif default_value is not None:
                return UserSettingModel(user_id, setting_name, default_value, available_for_llm)
            else:
                return None

    def add_update_user_setting(self, user_id, setting_name, setting_value, available_for_llm=False):
        with self.session_context(self.Session()) as session:
            existing_setting = (
                session.query(UserSetting)
                .filter(
                    UserSetting.user_id == user_id,
                    UserSetting.setting_name == setting_name,                    
                )
                .first()
            )

            if existing_setting:
                existing_setting.setting_value = setting_value
                existing_setting.available_for_llm = available_for_llm
            else:
                new_setting = UserSetting(
                    user_id=user_id,
                    setting_name=setting_name,
                    setting_value=setting_value,
                    available_for_llm=available_for_llm,
                )
                session.add(new_setting)

            session.commit()

    def delete_user_setting(self, user_id, setting_name):
        with self.session_context(self.Session()) as session:
            session.query(UserSetting).filter(
                UserSetting.user_id == user_id, UserSetting.setting_name == setting_name
            ).delete()

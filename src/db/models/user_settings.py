from src.db.database.tables import UserSetting
from src.db.models.domain.user_settings_model import UserSettingModel
from src.db.models.vector_database import VectorDatabase


class UserSettings(VectorDatabase):
    def create_user_setting(self, user_setting_model):
        with self.session_context(self.Session()) as session:
            db_model = UserSettingModel.to_database_model(user_setting_model)
            session.add(db_model)

    def get_user_setting(self, user_id, setting_name):
        with self.session_context(self.Session()) as session:
            db_model = (
                session.query(UserSetting)
                .filter(
                    UserSetting.user_id == user_id,
                    UserSetting.setting_name == setting_name,
                )
                .first()
            )
            return UserSettingModel.from_database_model(db_model) if db_model else None

    def add_update_user_setting(self, user_id, setting_name, setting_value):
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
            else:
                new_setting = UserSetting(
                    user_id=user_id,
                    setting_name=setting_name,
                    setting_value=setting_value,
                )
                session.add(new_setting)

            session.commit()

    def delete_user_setting(self, user_id, setting_name):
        with self.session_context(self.Session()) as session:
            session.query(UserSetting).filter(
                UserSetting.user_id == user_id, UserSetting.setting_name == setting_name
            ).delete()

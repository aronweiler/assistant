from src.shared.database.schema.tables import UserSetting
from src.shared.database.models.domain.user_settings_model import UserSettingModel
from src.shared.database.models.vector_database import VectorDatabase


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

    def cast_to_type(self, value, to_type):
        if to_type == bool:
            # If the type is already a boolean, just return it
            if isinstance(value, bool):
                return value

            return value.lower() in ("true", "1", "t")
        else:
            return to_type(value)

    def get_user_setting(
        self,
        user_id,
        setting_name,
        target_type: type = None,
        default_value=None,
        default_available_for_llm=False,
    ):
        with self.session_context(self.Session()) as session:
            db_model = (
                session.query(UserSetting)
                .filter(
                    UserSetting.user_id == user_id,
                    UserSetting.setting_name == setting_name,
                )
                .first()
            )

            if db_model:
                user_setting = UserSettingModel.from_database_model(db_model)

            elif default_value is not None:
                user_setting = UserSettingModel(
                    user_id, setting_name, default_value, default_available_for_llm
                )
            else:
                return None

            # Cast it to the target type if it is not None
            # I hate python's type system.
            # This would be so much better in a statically typed language.
            if target_type is not None:
                user_setting.setting_value = self.cast_to_type(
                    value=user_setting.setting_value, to_type=type(target_type)
                )
            elif default_value is not None:
                user_setting.setting_value = self.cast_to_type(
                    value=user_setting.setting_value, to_type=type(default_value)
                )

            return user_setting

    def add_update_user_setting(
        self, user_id, setting_name, setting_value, available_for_llm=False
    ):
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

# from typing import Union, List
# from memory.database.models import User, UserSetting
# from memory.models.vector_database import VectorDatabase

# class UserSettings(VectorDatabase):
#     def __init__(self, db_env_location):
#        super().__init__(db_env_location)

#     def get_settings_for_user(self, user:User) ->  List[UserSetting]:
#         
#             query = session.query(UserSetting).filter(UserSetting.user_id == user.id)

#             return query.all()
        
#     def update_add_setting_for_user(self, session, settings:List[UserSetting]):
        
#             for setting in settings:
#                 temp_setting = session.query(UserSetting).filter(UserSetting.user == user).first()

#                 if temp_setting is not None:
#                     temp_setting.name = setting.setting_name
#                     temp_setting.value = setting.setting_value
#                 else:            
#                     session.add(setting)

#     def delete_setting_for_user(self, user:User, setting_name:str):
#         
#             # only delete the setting if it exists
#             query = session.query(UserSetting).filter(UserSetting.user_id == user.id).filter(UserSetting.name == setting_name)
#             if query.count() > 0:
#                 query.delete()           
            
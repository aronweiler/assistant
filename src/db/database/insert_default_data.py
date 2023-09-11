# # Add the root path to the python path so we can import the database
# import sys
# import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# from src.db.database.models import ConversationRoleType, User, UserSetting, DocumentCollection

# def insert_users():
#     vector_db = VectorDatabase()

#     with vector_db.session_context(vector_db.Session()) as session:
#         aron = User(name="Aron Weiler", email="aronweiler@gmail.com", age=44, location="San Diego, CA")
#         aron.user_settings.append(UserSetting(setting_name="tts_voice", setting_value="Brian"))
#         aron.user_settings.append(UserSetting(setting_name="user_location", setting_value="San Diego, CA"))

#         session.add(aron)

#         gaia = User(name="Gaia Weiler", email="gaiaweiler@gmail.com", age=9, location="San Diego, CA")
#         gaia.user_settings.append(UserSetting(setting_name="tts_voice", setting_value="Joanna"))
#         gaia.user_settings.append(UserSetting(setting_name="user_location", setting_value="San Diego, CA"))

#         session.add(gaia)

#         gaia = User(name="Susan Workman", email="susanmae1129@gmail.com", age=3000, location="San Diego, CA")
#         gaia.user_settings.append(UserSetting(setting_name="tts_voice", setting_value="Amy"))
#         gaia.user_settings.append(UserSetting(setting_name="user_location", setting_value="San Diego, CA"))

#         session.add(gaia)
        
#         session.commit()

# if __name__ == "__main__":
#     ensure_conversation_role_types()
#     insert_users()
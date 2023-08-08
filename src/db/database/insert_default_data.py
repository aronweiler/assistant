# Add the root path to the python path so we can import the database
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from db.models.vector_database import VectorDatabase
from db.database.models import ConversationRoleType, User, UserSetting

db_env = "src/db/database/db.env"

def insert_conversation_role_types():
    vector_db = VectorDatabase(db_env)

    with vector_db.session_context(vector_db.Session()) as session:
        session.add(ConversationRoleType(role_type="system"))
        session.add(ConversationRoleType(role_type="assistant"))
        session.add(ConversationRoleType(role_type="user"))
        session.add(ConversationRoleType(role_type="function"))
        session.add(ConversationRoleType(role_type="error"))
        session.commit()

def insert_users():
    vector_db = VectorDatabase(db_env)

    with vector_db.session_context(vector_db.Session()) as session:
        aron = User(name="Aron Weiler", email="aronweiler@gmail.com")
        aron.user_settings.append(UserSetting(setting_name="tts_voice", setting_value="Brian"))
        aron.user_settings.append(UserSetting(setting_name="personality_keywords", setting_value="serious, professional, friendly"))
        aron.user_settings.append(UserSetting(setting_name="speech_rate", setting_value="150"))        
        aron.user_settings.append(UserSetting(setting_name="user_location", setting_value="San Diego, CA"))


        gaia = User(name="Gaia Weiler", email="gaiaweiler@gmail.com")
        gaia.user_settings.append(UserSetting(setting_name="tts_voice", setting_value="Joanna"))
        gaia.user_settings.append(UserSetting(setting_name="personality_keywords", setting_value="Funny, silly, friendly"))
        gaia.user_settings.append(UserSetting(setting_name="speech_rate", setting_value="120"))
        gaia.user_settings.append(UserSetting(setting_name="user_location", setting_value="San Diego, CA"))

        session.add(gaia)
        session.add(aron)
        
        session.commit()

if __name__ == "__main__":
    insert_conversation_role_types()
    insert_users()
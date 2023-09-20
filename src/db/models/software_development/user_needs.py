from typing import List

from src.db.database.models import UserNeeds as DBUserNeeds
from src.db.models.software_development.domain.user_needs_model import UserNeedsModel
from src.db.models.vector_database import VectorDatabase

class UserNeeds(VectorDatabase):
    def create_user_need(self, project_id, category, text) -> UserNeedsModel:
        with self.session_context(self.Session()) as session:
            user_need = DBUserNeeds(project_id=project_id, category=category, text=text)
            session.add(user_need)
            session.commit()
            return UserNeedsModel.from_database_model(user_need)

    def get_user_need(self, user_need_id) -> UserNeedsModel:
        with self.session_context(self.Session()) as session:
            user_need = session.query(DBUserNeeds).filter(DBUserNeeds.id == user_need_id).first()
            return UserNeedsModel.from_database_model(user_need)
        
    def get_user_needs_in_project(self, project_id) -> List[UserNeedsModel]:
        with self.session_context(self.Session()) as session:
            user_needs = session.query(DBUserNeeds).filter(DBUserNeeds.project_id == project_id).all()            
            return [UserNeedsModel.from_database_model(u) for u in user_needs]

    def update_user_need(self, user_need_id, new_category, new_text) -> UserNeedsModel:
        with self.session_context(self.Session()) as session:
            user_need = session.query(DBUserNeeds).filter(DBUserNeeds.id == user_need_id).first()
            user_need.category = new_category
            user_need.text = new_text
            session.commit()
            return UserNeedsModel.from_database_model(user_need)

    def delete_user_need(self, user_need_id) -> bool:
        with self.session_context(self.Session()) as session:
            user_need = session.query(DBUserNeeds).filter(DBUserNeeds.id == user_need_id).first()
            if user_need:
                session.delete(user_need)
                session.commit()
                return True
            return False

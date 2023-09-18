from typing import List

from src.db.database.models import Requirements as DBRequirements
from src.db.models.software_development.domain.requirements_model import RequirementsModel
from src.db.models.vector_database import VectorDatabase

class Requirements(VectorDatabase):
    def create_requirement(self, project_id, user_need_id, category, text) -> RequirementsModel:
        with self.session_context(self.Session()) as session:
            requirement = DBRequirements(project_id=project_id, user_need_id=user_need_id, category=category, text=text)
            session.add(requirement)
            session.commit()
            return RequirementsModel.from_database_model(requirement)

    def get_requirement(self, requirement_id) -> RequirementsModel:
        with self.session_context(self.Session()) as session:
            requirement = session.query(DBRequirements).filter(DBRequirements.id == requirement_id).first()
            return RequirementsModel.from_database_model(requirement)
        
    def get_requirements_for_user_need(self, user_need_id) -> List[RequirementsModel]:
        with self.session_context(self.Session()) as session:
            requirements = session.query(DBRequirements).filter(DBRequirements.user_need_id == user_need_id).all()            
            return [RequirementsModel.from_database_model(r) for r in requirements]
        
    def get_requirements_for_project(self, project_id) -> List[RequirementsModel]:
        with self.session_context(self.Session()) as session:
            requirements = session.query(DBRequirements).filter(DBRequirements.project_id == project_id).all()            
            return [RequirementsModel.from_database_model(r) for r in requirements]

    def update_requirement(self, requirement_id, new_user_need_id, new_category, new_text) -> RequirementsModel:
        with self.session_context(self.Session()) as session:
            requirement = session.query(DBRequirements).filter(DBRequirements.id == requirement_id).first()
            requirement.user_need_id = new_user_need_id
            requirement.category = new_category
            requirement.text = new_text
            session.commit()
            return RequirementsModel.from_database_model(requirement)

    def delete_requirement(self, requirement_id) -> bool:
        with self.session_context(self.Session()) as session:
            requirement = session.query(DBRequirements).filter(DBRequirements.id == requirement_id).first()
            if requirement:
                session.delete(requirement)
                session.commit()
                return True
            return False

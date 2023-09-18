from typing import List

from src.db.database.models import Project as DBProject
from src.db.models.software_development.domain.project_model import ProjectModel
from src.db.models.vector_database import VectorDatabase

class Projects(VectorDatabase):
    def create_project(self, project_name) -> ProjectModel:
        with self.session_context(self.Session()) as session:
            project = DBProject(project_name=project_name)
            session.add(project)
            session.commit()
            return ProjectModel.from_database_model(project)

    def get_project(self, project_id) -> ProjectModel:
        with self.session_context(self.Session()) as session:
            project = session.query(DBProject).filter(DBProject.id == project_id).first()
            return ProjectModel.from_database_model(project)
        
    def get_projects(self) -> List[ProjectModel]:
        with self.session_context(self.Session()) as session:
            projects = session.query(DBProject).all()            
            return [ProjectModel.from_database_model(p) for p in projects]

    def update_project(self, project_id, new_project_name) -> ProjectModel:
        with self.session_context(self.Session()) as session:
            project = session.query(DBProject).filter(DBProject.id == project_id).first()
            project.project_name = new_project_name
            session.commit()
            return ProjectModel.from_database_model(project)

    def delete_project(self, project_id) -> bool:
        with self.session_context(self.Session()) as session:
            project = session.query(DBProject).filter(DBProject.id == project_id).first()
            if project:
                session.delete(project)
                session.commit()
                return True
            return False

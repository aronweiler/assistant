from src.db.database.models import Project as DBProject

class ProjectModel:
    def __init__(self, id, project_name, record_created=None):
        self.id = id
        self.project_name = project_name
        self.record_created = record_created

    def to_database_model(self):
        return DBProject(
            id=self.id,
            project_name=self.project_name,
            record_created=self.record_created
        )

    @classmethod
    def from_database_model(cls, db_project):
        if db_project is None:
            return None
        
        return cls(
            id=db_project.id,
            project_name=db_project.project_name,
            record_created=db_project.record_created
        )

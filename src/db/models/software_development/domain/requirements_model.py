from src.db.database.models import Requirements as DBRequirements

class RequirementsModel:
    def __init__(self, id, project_id, user_need_id, category, text):
        self.id = id
        self.project_id = project_id
        self.user_need_id = user_need_id
        self.category = category
        self.text = text

    def to_database_model(self):
        return DBRequirements(
            id=self.id,
            project_id=self.project_id,
            user_need_id=self.user_need_id,
            category=self.category,
            text=self.text,
        )

    @classmethod
    def from_database_model(cls, db_requirements):
        if db_requirements is None:
            return None
        
        return cls(
            id=db_requirements.id,
            project_id=db_requirements.project_id,
            user_need_id=db_requirements.user_need_id,
            category=db_requirements.category,
            text=db_requirements.text,
        )

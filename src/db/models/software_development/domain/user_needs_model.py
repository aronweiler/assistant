from typing import List

from src.db.database.models import UserNeeds as DBUserNeeds
from src.db.models.software_development.domain.requirements_model import RequirementsModel

class UserNeedsModel:
    requirements = [] 

    def __init__(self, id, project_id, category, text):
        self.id = id
        self.project_id = project_id
        self.category = category
        self.text = text

    def to_database_model(self):
        return DBUserNeeds(
            id=self.id,
            project_id=self.project_id,
            category=self.category,
            text=self.text,
        )
    
    def to_dict(self):
        return vars(self)

    @classmethod
    def from_database_model(cls, db_user_needs):
        if db_user_needs is None:
            return None
        
        return cls(
            id=db_user_needs.id,
            project_id=db_user_needs.project_id,
            category=db_user_needs.category,
            text=db_user_needs.text,
        )
    
    

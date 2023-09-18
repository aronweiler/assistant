from src.db.database.models import DesignDecisions as DBDesignDecisions

class DesignDecisionsModel:

    def __init__(self, id, project_id, category, decision, details):
        self.id = id
        self.project_id = project_id
        self.category = category
        self.decision = decision
        self.details = details

    def to_database_model(self):
        return DBDesignDecisions(
            id=self.id,
            project_id=self.project_id,
            category=self.category,
            decision=self.decision,
            details=self.details,
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
            decision=db_user_needs.decision,
            details=db_user_needs.details,
        )
    
    

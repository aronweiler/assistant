from typing import List

from src.db.database.models import DesignDecisions as DBDesignDecisions
from src.db.models.software_development.domain.design_decisions_model import DesignDecisionsModel
from src.db.models.vector_database import VectorDatabase

class DesignDecisions(VectorDatabase):
    def create_design_decision(self, project_id, category, decision, details) -> DesignDecisionsModel:
        with self.session_context(self.Session()) as session:
            design_decision = DBDesignDecisions(
                project_id=project_id,
                category=category,
                decision=decision,
                details=details
            )
            session.add(design_decision)
            session.commit()
            return DesignDecisionsModel.from_database_model(design_decision)

    def get_design_decision(self, design_decision_id) -> DesignDecisionsModel:
        with self.session_context(self.Session()) as session:
            design_decision = session.query(DBDesignDecisions).filter(DBDesignDecisions.id == design_decision_id).first()
            return DesignDecisionsModel.from_database_model(design_decision)
        
    def get_design_decisions_in_project(self, project_id) -> List[DesignDecisionsModel]:
        with self.session_context(self.Session()) as session:
            design_decisions = session.query(DBDesignDecisions).filter(DBDesignDecisions.project_id == project_id).all()            
            return [DesignDecisionsModel.from_database_model(d) for d in design_decisions]

    def update_design_decision(self, design_decision_id, new_category, new_decision, new_details) -> DesignDecisionsModel:
        with self.session_context(self.Session()) as session:
            design_decision = session.query(DBDesignDecisions).filter(DBDesignDecisions.id == design_decision_id).first()
            design_decision.category = new_category
            design_decision.decision = new_decision
            design_decision.details = new_details
            session.commit()
            return DesignDecisionsModel.from_database_model(design_decision)

    def delete_design_decision(self, design_decision_id) -> bool:
        with self.session_context(self.Session()) as session:
            design_decision = session.query(DBDesignDecisions).filter(DBDesignDecisions.id == design_decision_id).first()
            if design_decision:
                session.delete(design_decision)
                session.commit()
                return True
            return False

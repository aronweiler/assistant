from src.db.database.models import AdditionalDesignInputs as DBAdditionalDesignInputs
from src.db.models.software_development.domain.additional_design_inputs_model import AdditionalDesignInputsModel
from src.db.models.vector_database import VectorDatabase

class AdditionalDesignInputs(VectorDatabase):
    def create_design_input(self, project_id, requirement_id, file_id, description) -> AdditionalDesignInputsModel:
        with self.session_context(self.Session()) as session:
            design_input = DBAdditionalDesignInputs(project_id=project_id, requirement_id=requirement_id, file_id=file_id, description=description)
            session.add(design_input)
            session.commit()
            return AdditionalDesignInputsModel.from_database_model(design_input)

    def get_design_input(self, design_input_id) -> AdditionalDesignInputsModel:
        with self.session_context(self.Session()) as session:
            design_input = session.query(DBAdditionalDesignInputs).filter(DBAdditionalDesignInputs.id == design_input_id).first()
            return AdditionalDesignInputsModel.from_database_model(design_input)
        
    def get_design_inputs_for_project(self, project_id) -> list[AdditionalDesignInputsModel]:
        with self.session_context(self.Session()) as session:
            design_inputs = session.query(DBAdditionalDesignInputs).filter(DBAdditionalDesignInputs.project_id == project_id).all()
            return [AdditionalDesignInputsModel.from_database_model(design_input) for design_input in design_inputs]

    def update_design_input(self, design_input_id, requirement_id, new_file_id, new_description) -> AdditionalDesignInputsModel:
        with self.session_context(self.Session()) as session:
            design_input = session.query(DBAdditionalDesignInputs).filter(DBAdditionalDesignInputs.id == design_input_id).first()
            design_input.requirement_id = requirement_id
            design_input.file_id = new_file_id
            design_input.description = new_description
            session.commit()
            return AdditionalDesignInputsModel.from_database_model(design_input)

    def delete_design_input(self, design_input_id) -> bool:
        with self.session_context(self.Session()) as session:
            design_input = session.query(DBAdditionalDesignInputs).filter(DBAdditionalDesignInputs.id == design_input_id).first()
            if design_input:
                session.delete(design_input)
                session.commit()
                return True
            return False

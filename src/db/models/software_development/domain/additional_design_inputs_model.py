from src.db.database.models import AdditionalDesignInputs as DBAdditionalDesignInputs

class AdditionalDesignInputsModel:
    def __init__(self, id, project_id, requirement_id, file_id, description):
        self.id = id
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.file_id = file_id
        self.description = description

    def to_database_model(self):
        return DBAdditionalDesignInputs(
            id=self.id,
            project_id=self.project_id,
            requirement_id=self.requirement_id,
            file_id=self.file_id,
            description=self.description
        )

    @classmethod
    def from_database_model(cls, db_additional_design_inputs):
        if db_additional_design_inputs is None:
            return None
        
        return cls(
            id=db_additional_design_inputs.id,
            project_id=db_additional_design_inputs.project_id,
            requirement_id=db_additional_design_inputs.requirement_id,
            file_id=db_additional_design_inputs.file_id,
            description=db_additional_design_inputs.description            
        )

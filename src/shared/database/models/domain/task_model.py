from src.shared.database.schema.tables import Task


class TaskModel:
    def __init__(self, id, name, description, current_state, associated_user_id, external_task_id, record_updated):
        self.id = id
        self.name = name
        self.description = description
        self.current_state = current_state
        self.associated_user_id = associated_user_id
        self.external_task_id = external_task_id
        self.record_updated = record_updated

    def to_database_model(self):
        return Task(
            id=self.id,
            name=self.name,
            description=self.description,
            current_state=self.current_state,
            associated_user_id=self.associated_user_id,
            external_task_id=self.external_task_id,
            record_updated=self.record_updated
        )

    @classmethod
    def from_database_model(cls, db_task):
        if db_task is None:
            return None

        return cls(
            id=db_task.id,
            name=db_task.name,
            description=db_task.description,
            current_state=db_task.current_state,
            associated_user_id=db_task.associated_user_id,
            external_task_id=db_task.external_task_id,
            record_updated=db_task.record_updated
        )



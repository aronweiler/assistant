from src.shared.database.schema.tables import TaskHistory


class TaskHistoryModel:
    def __init__(self, id, task_id, state, description, record_updated):
        self.id = id
        self.task_id = task_id
        self.state = state
        self.description = description
        self.record_updated = record_updated

    def to_database_model(self):
        return TaskHistory(
            id=self.id,
            task_id=self.task_id,
            state=self.state,
            description=self.description,
            record_updated=self.record_updated
        )

    @classmethod
    def from_database_model(cls, db_task_history):
        if db_task_history is None:
            return None

        return cls(
            id=db_task_history.id,
            task_id=db_task_history.task_id,
            state=db_task_history.state,
            description=db_task_history.description,
            record_updated=db_task_history.record_updated
        )
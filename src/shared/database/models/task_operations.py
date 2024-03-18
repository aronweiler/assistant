from datetime import datetime
from typing import List

from src.shared.database.models.domain.task_history_model import TaskHistoryModel
from src.shared.database.models.vector_database import VectorDatabase
from src.shared.database.schema.tables import Task, TaskHistory
from src.shared.database.models.domain.task_model import TaskModel


class TaskOperations(VectorDatabase):
    def get_tasks_by_user_id(self, associated_user_id: int) -> List[TaskModel]:
        with self.session_context(self.Session()) as session:
            query = session.query(Task).filter(
                Task.associated_user_id == associated_user_id
            )
            return [TaskModel.from_database_model(task) for task in query.all()]

    def get_task_by_id(self, id: int) -> TaskModel:
        with self.session_context(self.Session()) as session:
            task = session.query(Task).filter(Task.id == id).first()
            return TaskModel.from_database_model(task)

    def get_task_by_external_id(self, external_task_id: str) -> TaskModel:
        with self.session_context(self.Session()) as session:
            task = (
                session.query(Task)
                .filter(Task.external_task_id == external_task_id)
                .first()
            )
            return TaskModel.from_database_model(task)

    def get_tasks_by_user_id_and_state(
        self, associated_user_id: int, current_state: str
    ) -> List[TaskModel]:
        with self.session_context(self.Session()) as session:
            query = session.query(Task).filter(
                Task.associated_user_id == associated_user_id,
                Task.current_state == current_state,
            )
            return [TaskModel.from_database_model(task) for task in query.all()]

    def create_task(
        self, name, description, current_state, associated_user_id, external_task_id
    ):
        with self.session_context(self.Session()) as session:
            # If the external_task_id already exists, then we should just update that one
            task = (
                session.query(Task)
                .filter(Task.external_task_id == external_task_id)
                .first()
            )
            if task:
                task.name = name
                task.description = description
                task.current_state = current_state
                task.associated_user_id = associated_user_id
                task.external_task_id = external_task_id
                task.record_updated = datetime.now()
                
                session.commit()
                task_id = task.id
            else:
                new_task = Task(
                    name=name,
                    description=description,
                    current_state=current_state,
                    associated_user_id=associated_user_id,
                    external_task_id=external_task_id,
                    record_updated=datetime.now(),
                )
                session.add(new_task)
                session.commit()
                task_id = new_task.id

            # Additionally, add the task history
            self._create_task_history(session, task_id, current_state, description)

    def update_task_state(
        self, external_task_id: int, current_state: str, description: str
    ) -> None:
        with self.session_context(self.Session()) as session:
            task = (
                session.query(Task)
                .filter(Task.external_task_id == external_task_id)
                .first()
            )
            if task:
                task.current_state = current_state
                task.description = description
                task.record_updated = datetime.now()
                session.commit()

            # Additionally, add the task history
            self._create_task_history(session, task.id, current_state, description)

    def _create_task_history(
        self, session, task_id: int, state: str, description: str
    ) -> None:
        new_task_history = TaskHistory(
            task_id=task_id,
            state=state,
            description=description,
            record_updated=datetime.now(),
        )
        session.add(new_task_history)
        session.commit()

    def get_task_history_by_task_id(self, task_id: int) -> List[TaskHistoryModel]:
        with self.session_context(self.Session()) as session:
            query = session.query(TaskHistory).filter(TaskHistory.task_id == task_id)
            return [
                TaskHistoryModel.from_database_model(history) for history in query.all()
            ]

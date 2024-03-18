# TODO:Put some of these into utilities in the AI folder

import logging
from src.shared.utilities.configuration_utilities import get_app_configuration
from src.shared.database.models.documents import Documents

from celery import current_task


def get_selected_embedding_name(collection_id):

    if collection_id == -1:
        return None

    collection = Documents().get_collection(collection_id)

    if not collection:
        return None

    return collection.embedding_name


def get_selected_collection_embedding_model_name(collection_id):
    embedding_name = get_selected_embedding_name(collection_id)

    if not embedding_name:
        return None

    key = get_app_configuration()["jarvis_ai"]["embedding_models"]["available"][
        embedding_name
    ]

    return key

def write_status(status: str, state="PROGRESS", log_level: str = "info"):
    from src.shared.database.models.task_operations import TaskOperations

    task_operations = TaskOperations()

    current_task.update_state(
        state="PROGRESS",
        meta={"status": status},
    )
    # Get the log level from the argument and log the message
    log_level = getattr(logging, log_level)
    log_level(status)

    task_operations.update_task_state(
        external_task_id=current_task.request.id,
        current_state=state,
        description=status,
    )
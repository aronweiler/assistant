# TODO:Put these into utilities in the AI folder

from src.shared.utilities.configuration_utilities import get_app_configuration
from src.shared.database.models.documents import Documents


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

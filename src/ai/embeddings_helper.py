import openai
from InstructorEmbedding import INSTRUCTOR

import src.utilities.configuration_utilities as configuration_utilities

from src.utilities.configuration_utilities import get_app_configuration

local_embeddings_model = None


def get_local_embeddings_model(model_name):
    global local_embeddings_model
    
    if not local_embeddings_model:
        model_config = configuration_utilities.get_app_configuration()["jarvis_ai"][
            "embedding_models"
        ].get(model_name, None)

        if not model_config:
            raise Exception(f"Unknown model name {model_name}")

        local_embeddings_model = INSTRUCTOR(model_config["path"])

    return local_embeddings_model


def get_embedding(
    text: str,
    collection_type:str,
    instruction: str = None,
):
    if collection_type.lower().startswith("remote"):
        model_name = get_app_configuration()["jarvis_ai"]["embedding_models"][
            "default"
        ]["remote"]
    elif collection_type.lower().startswith("local"):
        model_name = get_app_configuration()["jarvis_ai"]["embedding_models"][
            "default"
        ]["local"]
    else:
        raise Exception(f"Unknown collection type {collection_type}")

    return get_embedding_with_model(text=text, model_name=model_name, instruction=instruction)


def get_embedding_with_model(text: str, model_name: str, instruction: str = None):
    # You're special, OpenAI
    if model_name == "text-embedding-ada-002":
        return openai.Embedding.create(input=[text], model=model_name)["data"][0][
            "embedding"
        ]
    else:
        model = get_local_embeddings_model(model_name)

        return model.encode([[instruction, text]])

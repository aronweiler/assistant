import openai
import src.utilities.configuration_utilities as configuration_utilities

from src.utilities.configuration_utilities import get_app_configuration

local_embeddings_model = None


def get_local_embeddings_model(model_name):
    from InstructorEmbedding import INSTRUCTOR

    global local_embeddings_model

    if not local_embeddings_model:
        model_config = configuration_utilities.get_app_configuration()["jarvis_ai"][
            "embedding_models"
        ].get(model_name, None)

        if not model_config:
            raise Exception(f"Unknown model name {model_name}")

        local_embeddings_model = INSTRUCTOR(model_config["path"])

    return local_embeddings_model


def get_embedding_by_name(
    text: str,
    embedding_name: str,
    instruction: str = None,
):
    model_name = get_app_configuration()["jarvis_ai"]["embedding_models"][
        "available"
    ].get(embedding_name, None)

    if not model_name:
        raise Exception(f"Unknown embedding name {embedding_name}")

    return get_embedding_by_model(
        text=text, model_name=model_name, instruction=instruction
    )


def find_key_by_value(d, value):
    for key, val in d.items():
        if val == value:
            return key
    return None


def get_embedding_by_model(text: str, model_name: str, instruction: str = None):

    available_models = get_app_configuration()["jarvis_ai"]["embedding_models"][
        "available"
    ]

    key = find_key_by_value(available_models, model_name)

    if not key:
        raise Exception(f"Unknown model name {model_name}")

    embedding_config = get_app_configuration()["jarvis_ai"]["embedding_models"][
        model_name
    ]

    # You're special, OpenAI
    if key.lower().startswith("openai"):
        embedding = openai.embeddings.create(
            input=text,
            model=model_name,
            dimensions=embedding_config["dimensions"],
        )

        return embedding.data[0].embedding
    else:
        model = get_local_embeddings_model(model_name)

        return [
            m.item()
            for m in model.encode([[instruction, text]], convert_to_numpy=False)[0]
        ]

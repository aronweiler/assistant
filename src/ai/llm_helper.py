from langchain.chat_models import ChatOpenAI

from utilities.openai_utilities import get_openai_api_key

def get_llm(model_configuration, **kwargs):
    """Returns the LLM for the specified model configuration."""

    if model_configuration.llm_type == "open_ai":
        return _get_openai_llm(model_configuration, **kwargs)
    elif model_configuration.llm_type == "local":
        return _get_local_llm(model_configuration, **kwargs)

def _get_openai_llm(model_configuration, **kwargs):
    llm = ChatOpenAI(
        model=model_configuration.model,
        temperature=model_configuration.temperature,
        max_retries=model_configuration.max_retries,
        max_tokens=model_configuration.max_completion_tokens,
        openai_api_key=get_openai_api_key(),
        verbose=True,
        **kwargs
    )

    return llm

def _get_local_llm(model_configuration, **kwargs):
    raise NotImplementedError("Local LLMs are not yet supported.")
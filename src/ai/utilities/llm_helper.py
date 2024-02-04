import os

from enum import Enum

from langchain_openai import ChatOpenAI
from langchain.llms.llamacpp import LlamaCpp
from langchain_core.language_models import BaseLanguageModel

from src.utilities.openai_utilities import get_openai_api_key
from src.configuration.assistant_configuration import ModelConfiguration
import src.utilities.configuration_utilities as configuration_utilities

# Singleton instance of Llama2 LLM to avoid reinitialization
llama2_llm = None

# Constants for environment variables
OFFLOAD_TO_GPU_LAYERS_ENV = "OFFLOAD_TO_GPU_LAYERS"


class LLMType(Enum):
    """Enum for the type of prompt to use."""

    LLAMA2 = "llama2"
    OPENAI = "openai"
    LUNA = "luna"


def get_llm(model_configuration: ModelConfiguration, **kwargs) -> BaseLanguageModel:
    """Returns the LLM for the specified model configuration."""
    if isinstance(model_configuration, dict):
        model_configuration = ModelConfiguration(**model_configuration)

    llm_type = model_configuration.llm_type
    if llm_type == LLMType.OPENAI.value:
        return _get_openai_llm(model_configuration, **kwargs)
    elif llm_type in (LLMType.LLAMA2.value, LLMType.LUNA.value):
        return _get_llama2_llm(model_configuration, **kwargs)
    else:
        raise ValueError(f"Unsupported LLM type: {llm_type}")


def get_tool_llm(configuration: dict, func_name: str, **kwargs) -> BaseLanguageModel:
    """Retrieves the LLM based on the tool configuration."""
    tool_config = configuration_utilities.get_tool_configuration(
        configuration=configuration, func_name=func_name
    )

    return get_llm(model_configuration=tool_config["model_configuration"], **kwargs)


def _get_openai_llm(model_configuration, **kwargs):
    """Initializes and returns an OpenAI LLM instance."""
    max_tokens = model_configuration.max_completion_tokens
    max_tokens = max_tokens if max_tokens > 0 else None

    if "model_kwargs" not in kwargs:
        kwargs["model_kwargs"] = model_configuration.model_kwargs
    else:
        if model_configuration.model_kwargs:
            kwargs["model_kwargs"].update(model_configuration.model_kwargs)

    llm = ChatOpenAI(
        model=model_configuration.model,
        temperature=model_configuration.temperature,
        max_retries=model_configuration.max_retries,
        max_tokens=max_tokens,
        openai_api_key=get_openai_api_key(),
        verbose=True,
        **kwargs,
    )

    return llm


def _get_llama2_llm(model_configuration: ModelConfiguration, **kwargs):
    """Initializes and returns a LlamaCpp LLM instance, reusing a singleton if already initialized."""
    global llama2_llm

    if llama2_llm:
        return llama2_llm

    offload_layers = _get_offload_layers_from_env()

    llama2_llm = LlamaCpp(
        model_path=model_configuration.model,
        n_ctx=model_configuration.max_model_supported_tokens,
        max_tokens=model_configuration.max_completion_tokens
        if model_configuration.max_completion_tokens > 0
        else None,
        temperature=model_configuration.temperature,
        n_gpu_layers=offload_layers,
        verbose=True,
    )

    return llama2_llm


def _get_offload_layers_from_env():
    """Retrieves and converts the offload layers environment variable to an integer."""
    offload_layers_str = os.environ.get(OFFLOAD_TO_GPU_LAYERS_ENV)
    return int(offload_layers_str) if offload_layers_str is not None else None

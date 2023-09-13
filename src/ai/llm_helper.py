import os
import importlib

from enum import Enum

from langchain.chat_models import ChatOpenAI
from langchain.llms.llamacpp import LlamaCpp

from src.utilities.openai_utilities import get_openai_api_key
from src.configuration.assistant_configuration import ModelConfiguration

llama2_llm = None

class LLMType(Enum):
    """Enum for the type of prompt to use."""

    LLAMA2 = "llama2"
    OPENAI = "openai"
    LUNA = "luna"

def get_prompt(prompt_type: LLMType, prompt_name: str):
    # Get the prompt from the right file- the folder structure looks like this:
    # ai/prompts/{prompt_type}_prompts.py

    # Get the path to the prompts folder
    #prompts_path = os.path.join(os.path.dirname(__file__), "prompts")

    # Construct the module name
    module_name = f"src.ai.prompts.{prompt_type}_prompts"

    # Import the module using importlib
    prompt_module = importlib.import_module(module_name)

    # Get the prompt from the prompt module
    prompt = getattr(prompt_module, prompt_name)

    return prompt

def get_llm(model_configuration: ModelConfiguration, **kwargs):
    """Returns the LLM for the specified model configuration."""

    if model_configuration.llm_type == LLMType.OPENAI.value:
        return _get_openai_llm(model_configuration, **kwargs)
    elif model_configuration.llm_type == LLMType.LLAMA2.value or model_configuration.llm_type == LLMType.LUNA.value:
        return _get_llama2_llm(model_configuration, **kwargs)

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

def _get_llama2_llm(model_configuration: ModelConfiguration, **kwargs):
    """Returns the local LLM (llama2 config) for the specified model configuration."""

    global llama2_llm

    if llama2_llm:
        return llama2_llm

    # Get the offload_layers from the os environment
    offload_layers = os.environ.get("OFFLOAD_TO_GPU_LAYERS", None)

    llama2_llm = LlamaCpp(
        model_path=model_configuration.model,
        n_ctx=model_configuration.max_model_supported_tokens,
        max_tokens=model_configuration.max_completion_tokens,
        temperature=model_configuration.temperature,
        n_gpu_layers=offload_layers,
        verbose=True,
        #**kwargs
    )

    return llama2_llm

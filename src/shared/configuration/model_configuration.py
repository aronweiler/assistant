from pydantic import BaseModel


class ModelConfiguration(BaseModel):
    llm_type: str
    model: str
    temperature: float
    max_retries: int
    max_model_supported_tokens: int
    uses_conversation_history: bool
    max_conversation_history_tokens: int
    max_completion_tokens: int
    model_kwargs: dict = {}

    def __init__(self, **config_data):
        super().__init__(**config_data)

    @staticmethod
    def default() -> "ModelConfiguration":
        # Return a ModelConfiguration object with default values

        return ModelConfiguration(
            llm_type="openai",
            model="gpt-4-turbo-preview",
            temperature=0.0,
            max_retries=3,
            max_model_supported_tokens=128000,
            uses_conversation_history=False,
            max_conversation_history_tokens=0,
            max_completion_tokens=4096,
            model_kwargs={"seed": 500, "response_format": {"type": "json_object"}},
        )

class LLMArgumentsConfiguration:
    def __init__(
        self,
        model,
        temperature,
        max_supported_tokens,
        max_completion_tokens,
        tools,
        max_function_limit,
        db_env_location
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_supported_tokens = max_supported_tokens
        self.max_completion_tokens = max_completion_tokens
        self.tools = tools
        self.max_function_limit = max_function_limit
        self.db_env_location = db_env_location
        self.system_prompt = ''

    @staticmethod
    def from_dict(config: dict, tools):
        model = config["model"]
        temperature = config["temperature"]
        max_supported_tokens = config["max_supported_tokens"]
        max_completion_tokens = config["max_completion_tokens"]
        max_function_limit = config.get("max_function_limit", 5)
        db_env_location = config["db_env_location"]

        return LLMArgumentsConfiguration(
            model, temperature, max_supported_tokens, max_completion_tokens, tools, max_function_limit, db_env_location
        )

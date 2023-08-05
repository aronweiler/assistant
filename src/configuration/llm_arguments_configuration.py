class LLMArgumentsConfiguration:
    def __init__(
        self,
        model,
        temperature,
        max_supported_tokens,
        max_completion_tokens,
        tools,
        max_function_limit
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_supported_tokens = max_supported_tokens
        self.max_completion_tokens = max_completion_tokens
        self.tools = tools
        self.max_function_limit = max_function_limit

    @staticmethod
    def from_dict(config: dict, tools):
        model = config["model"]
        temperature = config["temperature"]
        max_supported_tokens = config["max_supported_tokens"]
        max_completion_tokens = config["max_completion_tokens"]
        max_function_limit = config.get("max_function_limit", 5)

        return LLMArgumentsConfiguration(
            model, temperature, max_supported_tokens, max_completion_tokens, tools, max_function_limit
        )

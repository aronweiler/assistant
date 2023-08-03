class LLMArgumentsConfiguration:
    def __init__(self, model, temperature, max_supported_tokens, conversation_history, trim_conversation_history_at_token_count, tools, system_prompts, include_system_info) -> None:
        self.model = model
        self.temperature = temperature
        self.max_supported_tokens = max_supported_tokens
        self.conversation_history = conversation_history
        self.trim_conversation_history_at_token_count = trim_conversation_history_at_token_count
        self.system_prompts = system_prompts
        self.include_system_info = include_system_info
        self.tools = tools


    @staticmethod
    def from_dict(config: dict, tools):
        model = config["model"]
        temperature = config["temperature"]
        max_supported_tokens = config["max_supported_tokens"]
        conversation_history = config["conversation_history"]
        trim_conversation_history_at_token_count = config["trim_conversation_history_at_token_count"]
        system_prompts = config["system_prompts"]
        include_system_info = config["include_system_info"]

        return LLMArgumentsConfiguration(model, temperature, max_supported_tokens, conversation_history, trim_conversation_history_at_token_count, tools, system_prompts, include_system_info)

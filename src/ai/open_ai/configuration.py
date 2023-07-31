from ai.open_ai.tools.tool_loader import ToolLoader


class OpenAIConfiguration:
    def __init__(self, json_args):
        self.model = json_args.get("model", "gpt-3.5-turbo")
        self.use_memory = json_args.get("use_memory", False)
        self.prompt = json_args.get("prompt", None)
        self.chat_model = json_args.get("chat_model", False)
        self.ai_temp = json_args.get("ai_temp", 0)
        self.verbose = json_args.get("verbose", False)
        self.max_tokens = json_args.get("max_tokens", 4096)
        self.tools = ToolLoader.load_tools_from_json(json_args.get("tools", []))

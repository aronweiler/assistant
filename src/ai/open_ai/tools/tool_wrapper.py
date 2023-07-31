class OpenAIToolWrapper:
    def __init__(
        self, module, class_name, name, tool_configuration
    ):
        self.tool_module = module
        self.tool_class = class_name
        self.name = name
        self.tool_configuration = tool_configuration

        # These will be set after init
        self.open_ai_tool = None
        self.open_ai_function = None

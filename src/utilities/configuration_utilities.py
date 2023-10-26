


def get_tool_configuration(configuration: dict, func_name: str) -> dict:
    return configuration.get(func_name, "default")

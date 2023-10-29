


def get_tool_configuration(configuration: dict, func_name: str) -> dict:
    if func_name in configuration['tool_configurations']:
        return configuration['tool_configurations'][func_name]
    
    return configuration['tool_configurations']['default']

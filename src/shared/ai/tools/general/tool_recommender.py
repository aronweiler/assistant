from typing import List


class ToolRecommender:
    def recommend_tool(self, explanation: str, tool_name: str = None):
        """Recommend a tool to use

        Args:
            explanation (str): The explanation for your choice (or lack thereof) of tool.
            tool_name (str): The name of the tool you are recommending. None if no tool is recommended.
        """
        return f"I recommend using '{tool_name}', because {explanation}"

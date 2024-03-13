from typing import List
from src.shared.ai.tools.tool_registry import register_tool
from src.shared.database.models.conversations import Conversations


@register_tool(
    display_name="Get Previous Tool Call Results",
    requires_documents=False,
    description="Get a previous tool call result (or results) by ID.",
    additional_instructions="Call this tool when you need to get the results of a previous tool call or calls.",
    category="General",
)
def get_previous_tool_call_results(tool_call_result_ids: List[int]):
    """
    Get a previous tool call result (or results) by ID.

    :param tool_call_result_ids: The IDs of the tool call result to retrieve.
    """

    if not isinstance(tool_call_result_ids, list):
        tool_call_result_ids = [tool_call_result_ids]

    conversations_helper = Conversations()

    results = []
    for tool_call_result_id in tool_call_result_ids:
        tool_call = conversations_helper.get_tool_call_results_by_id(
            tool_call_result_id
        )
        
        if not tool_call:
            results.append(f"Could not find tool call result with ID {tool_call_result_id}.  Make sure you're not just making up IDs.")
            continue
        
        results.append(
            f"{tool_call.record_created} - (ID: {tool_call.id}) Name: `{tool_call.tool_name}`, tool input: {tool_call.tool_arguments}, tool output: {tool_call.tool_results}"
        )

    return "\n----\n".join(results)

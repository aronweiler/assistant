from src.db.database.tables import ToolCallResults

class ToolCallResultsModel:
    def __init__(self, conversation_id, tool_name, tool_results, tool_arguments=None, id=None):
        self.id = id
        self.conversation_id = conversation_id
        self.tool_name = tool_name
        self.tool_arguments = tool_arguments
        self.tool_results = tool_results

    def to_database_model(self):
        return ToolCallResults(
            id=self.id,
            conversation_id=self.conversation_id,            
            tool_name=self.tool_name,
            tool_arguments=self.tool_arguments,
            tool_results=self.tool_results
        )

    @classmethod
    def from_database_model(cls, db_tool_call_results):
        if not db_tool_call_results:
            return None
        return cls(
            id=db_tool_call_results.id,
            conversation_id=db_tool_call_results.conversation_id,
            tool_name=db_tool_call_results.tool_name,
            tool_arguments=db_tool_call_results.tool_arguments,
            tool_results=db_tool_call_results.tool_results
        )
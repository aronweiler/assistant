from src.shared.database.schema.tables import ToolCallResults

class ToolCallResultsModel:
    def __init__(self, conversation_id, tool_name, tool_results, include_in_conversation = False, tool_arguments=None, id=None, record_created=None):
        self.id = id
        self.conversation_id = conversation_id
        self.tool_name = tool_name
        self.tool_arguments = tool_arguments
        self.tool_results = tool_results
        self.record_created = record_created
        self.include_in_conversation = include_in_conversation

    def to_database_model(self):
        return ToolCallResults(
            id=self.id,
            conversation_id=self.conversation_id,            
            tool_name=self.tool_name,
            tool_arguments=self.tool_arguments,
            tool_results=self.tool_results,
            record_created=self.record_created,
            include_in_conversation=self.include_in_conversation,
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
            tool_results=db_tool_call_results.tool_results,
            record_created=db_tool_call_results.record_created,
            include_in_conversation=db_tool_call_results.include_in_conversation,
        )
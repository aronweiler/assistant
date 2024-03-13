from src.shared.ai.conversations.conversation_manager import ConversationManager
from src.shared.ai.tools.tool_registry import register_tool, tool_class


@register_tool(
    display_name="Stand Alone Example Tool",    
    # Does the tool require documents to be used?
    requires_documents=False, 
    description="Stand alone example tool description.  This is used if the help text is empty.",
    additional_instructions="Additional instructions for the tool, such as how to use the arguments or what the tool does.",
    # The category the tool belongs to
    category="General",
    # If documents are required, what types of documents can this tool be used with?
    document_classes=["Document", "Code"],
    enabled_by_default=True,    
    help_text="Help text displayed to the user when configuring in the UI.  Description is used if this is empty.",
    # Should the tool be included in conversation memory so that the LLM can access the results?
    include_in_conversation=True,
    # Does this tool require a code repository, such as GitLab or GitHub to be used?
    requires_repository=False,
    # Should the results of this tool be returned directly to the user (direct), or returned to the LLM for interpretation?
    return_direct=False
)
def stand_alone_example_tool_function(tool_argument: str) -> str:
    return "example tool return value"

# This is the same tool as above, but implemented as a class that takes in the configuration and conversation manager
# This is useful if you need to access the configuration or conversation manager in your tool
# This is also useful if you need to maintain state between calls to the tool
@tool_class
class ExampleToolClass:
    def __init__(self, configuration: dict, conversation_manager: ConversationManager):
        self.configuration = configuration
        self.conversation_manager = conversation_manager

    @register_tool(
        display_name="Class-Based Example Tool",    
        # Does the tool require documents to be used?
        requires_documents=False, 
        description="Class-based example tool description.  This is used if the help text is empty.",
        additional_instructions="Additional instructions for the tool, such as how to use the arguments or what the tool does.",
        # The category the tool belongs to
        category="General",
        # If documents are required, what types of documents can this tool be used with?
        document_classes=["Document", "Code"],
        enabled_by_default=True,    
        help_text="Help text displayed to the user when configuring in the UI.  Description is used if this is empty.",
        # Should the tool be included in conversation memory so that the LLM can access the results?
        include_in_conversation=True,
        # Does this tool require a code repository, such as GitLab or GitHub to be used?
        requires_repository=False,
        # Should the results of this tool be returned directly to the user (direct), or returned to the LLM for interpretation?
        return_direct=False
    )
    def class_based_example_tool_function(self, tool_argument: str) -> str:
        return "example tool return value"
from langchain.schema.messages import BaseMessage

class ChatMessage(BaseMessage):
    id: int = None    

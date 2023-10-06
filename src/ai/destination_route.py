from src.ai.destinations.destination_base import DestinationBase

class DestinationRoute:
    def __init__(self, name, description, is_default, requires_documents, instance):
        self.name = name
        self.description = description
        self.is_default = is_default
        self.requires_documents = requires_documents
        self.instance:DestinationBase = instance
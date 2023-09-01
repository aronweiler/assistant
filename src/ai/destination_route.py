from ai.destinations.destination_base import DestinationBase

class DestinationRoute:
    def __init__(self, name, description, is_default, instance):
        self.name = name
        self.description = description
        self.is_default = is_default
        self.instance:DestinationBase = instance
from abc import ABC, abstractmethod, abstractproperty

# Abstract class that defines the properties needed by the derived classes
class BaseTool(ABC):
    name = None
    description = None

    @abstractmethod
    def run(self):
        pass
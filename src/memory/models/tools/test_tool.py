import inspect
from abc import ABC, abstractmethod, abstractproperty

# Abstract class that defines the properties needed by the derived classes
class BaseTool(ABC):
    name = None
    description = None

    @abstractmethod
    def run(self):
        pass


class ClassPropertiesExtractor:
    def __init__(self, target_class):
        self.target_class = target_class

    def extract_properties(self):
        properties = []
        for name, value in inspect.getmembers(self.target_class):
            # Exclude properties that start with underscore (private) and methods
            if not name.startswith('_') and not inspect.isroutine(value):
                properties.append(name)
        return properties
    
    def extract_functions_with_parameters(self, target_class):
        functions_with_parameters = {}
        for name, value in inspect.getmembers(target_class):
            if inspect.ismethod(value) or inspect.isfunction(value):
                signature = inspect.signature(value)
                parameters = list(signature.parameters.values())
                if not name.startswith('_') and parameters:
                    function_info = {
                        'parameters': [],
                        'docstring': inspect.getdoc(value) or '',
                    }
                    for param in parameters:
                        param_info = {
                            'name': param.name,
                            'type': param.annotation if param.annotation != inspect.Parameter.empty else None,
                        }
                        function_info['parameters'].append(param_info)
                    functions_with_parameters[name] = function_info
        return functions_with_parameters

# Example usage with a sample class
class SampleClass(BaseTool):
    name = "John Doe"
    description = "This is a sample class"

    def run(self, location:str, date:str):
        """Gets the weather for a given location and date.

        Args:
            location (string): The location to get the weather for.  Should be a city and state, e.g. San Francisco, CA.
            date (string): The date to get the weather for.  Should be in the format YYYY-MM-DD.
        """
        super().run()


# Create an instance of ClassPropertiesExtractor with SampleClass as an argument
extractor = ClassPropertiesExtractor(SampleClass)

SampleClass()  # Output: John Doe

# Get the list of properties from the SampleClass
properties_list = extractor.extract_properties()
functions_with_parameters = extractor.extract_functions_with_parameters(SampleClass)

print(properties_list)  # Output: ['age', 'location', 'name']
print(functions_with_parameters)  # Output: ['age', 'location', 'name']
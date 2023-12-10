from typing import List, Optional

class CodeDependency:
    """Represents a code dependency.

    Attributes:
        name (str): The name of the dependency.
        dependencies (List["CodeDependency"]): A list of dependencies for this code dependency.
    """

    def __init__(self, name: str, dependencies: Optional[List["CodeDependency"]] = None):
        """Initializes a new instance of the CodeDependency class.

        Args:
            name (str): The name of the dependency.
            dependencies (Optional[List["CodeDependency"]]): A list of dependencies for this code dependency.
                If None, it will be initialized as an empty list.
        """
        self.name = name
        self.dependencies = dependencies if dependencies is not None else []

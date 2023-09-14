from typing import List

class CodeDependency:
    name: str
    dependencies: List["CodeDependency"]

    def __init__(self, name: str, dependencies: List["CodeDependency"] = []):
        self.name = name
        self.dependencies = dependencies
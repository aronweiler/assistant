from abc import ABC


class DependencyAnalyzerBase(ABC):

    def process_code(self, directory: str) -> dict:
        pass

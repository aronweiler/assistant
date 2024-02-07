from abc import ABC


class DependencyAnalyzerBase(ABC):
    _PARSABLE_EXTENSIONS = ()

    def process_code(self, directory: str) -> dict:
        pass

from abc import ABC


class DependencyAnalyzerBase(ABC):
    _PARSABLE_EXTENSIONS = ()

    def process_code_directory(self, directory: str) -> dict:
        pass
    
    def process_code_file(self, code_file, base_directory: str = None) -> dict:
        pass

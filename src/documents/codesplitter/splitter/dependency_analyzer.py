import os
import sys


sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)

from src.documents.codesplitter.splitter.cpp.cpp_analyzer import CppAnalyzer
from src.documents.codesplitter.splitter.python.python_analyzer import PythonAnalyzer


class DependencyAnalyzer:
    supported_analyzers = [PythonAnalyzer, CppAnalyzer]

    def __init__(self):
        self.analyzers = {}
        # Assuming PythonAnalyzer and CppAnalyzer are already defined elsewhere
        for analyzer_class in self.supported_analyzers:
            for extension in analyzer_class._PARSABLE_EXTENSIONS:
                self.analyzers[extension] = analyzer_class()

    def process_code_file(self, code_file: str, base_directory: str = None) -> list:
        if base_directory is None:
            base_directory = os.path.dirname(code_file)
            
        file_extension = os.path.splitext(code_file)[1]
        for extension, analyzer in self.analyzers.items():
            if file_extension.strip() != '' and file_extension in analyzer._PARSABLE_EXTENSIONS:
                
                return analyzer.process_code_file(code_file, base_directory)
            
        return []


if __name__ == "__main__":
    analyzer = DependencyAnalyzer()
    results = analyzer.process_code_file("/Repos/assistant/about.py")    
    for result in results['dependencies']:
        print(f"{results['file']} : {result}")

    results = analyzer.process_code_file("C:\Repos\sample_docs\cpp\Dave\StateMachine-Code_Only\Motor.cpp")
    for result in results['dependencies']:
        print(f"{results['file']} : {result}")

import os
import ast
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../"))
)

from src.documents.codesplitter.splitter.dependency_analyzer_base import (
    DependencyAnalyzerBase,
)


class PythonAnalyzer(DependencyAnalyzerBase):
    _PARSABLE_EXTENSIONS = ".py"

    def process_code_file(self, code_file: str) -> dict:
        # Ensure the code_file is a file and not a directory
        if not os.path.isfile(code_file):
            raise ValueError(f"{code_file} is not a file")

        with open(code_file, "r", encoding="utf-8") as file:
            tree = ast.parse(file.read(), filename=code_file)
            dependencies = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    dependencies.append(node.names[0].name)

        return {"file": code_file, "dependencies": dependencies}

    def process_code_directory(self, directory: str) -> list:
        results = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(self._PARSABLE_EXTENSIONS):
                    full_path = os.path.join(root, file)
                    result = self._analyze_file(full_path)
                    results.append(result)
        return results

    def _analyze_file(self, file_path: str) -> dict:
        with open(file_path, "r", encoding="utf-8") as file:
            tree = ast.parse(file.read(), filename=file_path)
            dependencies = []
            for node in ast.walk(tree):
                if type(node) in (ast.Import, ast.ImportFrom):
                    dependencies.append(node.names[0].name)

        return {"file": file_path, "dependencies": dependencies}


if __name__ == "__main__":
    analyzer = PythonAnalyzer()
    results = analyzer.process_code("/repos/assistant/src")
    for result in results:
        print(f"{result['file']} : {result['dependencies']}")

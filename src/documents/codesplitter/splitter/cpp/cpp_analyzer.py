import os
import pathlib
import sys
import clang.cindex

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../"))
)

from src.documents.codesplitter.splitter.dependency_analyzer_base import (
    DependencyAnalyzerBase,
)


class CppAnalyzer(DependencyAnalyzerBase):
    _PARSABLE_EXTENSIONS = (".c", ".cc", ".cpp", ".h", ".hh", ".hpp")

    def process_code_file(self, code_file):
        allowed_include_paths = [os.path.dirname(code_file)]
        result = self._analyze_file(code_file, allowed_include_paths)
        return result

    def process_code_directory(self, directory):
        results = []
        allowed_include_paths = [os.path.dirname(directory)]

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(self._PARSABLE_EXTENSIONS):
                    full_path = os.path.join(root, file)
                    result = self._analyze_file(full_path, allowed_include_paths)
                    results.append(result)

        return results

    def _analyze_file(self, file_path, allowed_include_paths):
        index = clang.cindex.Index.create()
        tu = index.parse(file_path)
        dependencies = self._get_dependencies(tu, allowed_include_paths)

        return {
            "file": file_path,
            "dependencies": dependencies,
        }

    def _get_dependencies(self, tu, allowed_include_paths):
        include_files = []
        dependencies = list(tu.get_includes())
        for include_obj in dependencies:
            if self._is_node_in_allowed_path(
                include_obj.include.name, allowed_include_paths
            ):
                dependency_name = include_obj.include.name
                # Strip everything before the last / or \ to get the file name
                dependency_name = dependency_name.split("/")[-1]
                include_files.append(dependency_name)
        
        return include_files

    def _is_node_in_allowed_path(self, node, allowed_include_paths):
        if isinstance(node, str):
            node_path = pathlib.Path(node)
        else:
            if node.location.file is None:
                # Check the display name
                node_path = pathlib.Path(node.displayname)
            else:
                node_path = pathlib.Path(node.location.file.name)

        for allowed_path in allowed_include_paths:
            if node_path.is_relative_to(allowed_path):
                return True

        return False


if __name__ == "__main__":
    analyzer = CppAnalyzer()
    results = analyzer.process_code(
        "/Repos/sample_docs/cpp/Dave/StateMachine-Code_Only"
    )
    print(
        "\n".join(
            [f"{result['file']} : {result['dependencies']}" for result in results]
        )
    )

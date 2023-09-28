import re
import os
import pathlib

from src.documents.codesplitter.node_types import NodeType

from src.documents.codesplitter.splitter.splitter_base import SplitterBase

import clang.cindex
from clang.cindex import CursorKind


class CppSplitter(SplitterBase):
    _PARSABLE_EXTENSIONS = (".c", ".cc", ".cpp", ".h", ".hh", ".hpp")

    _FUNCTION_TYPES = (CursorKind.CXX_METHOD, CursorKind.FUNCTION_DECL)

    _GENERIC_NODE_TYPE_MAP = {
        CursorKind.CXX_METHOD: NodeType.CLASS_METHOD,
        CursorKind.FUNCTION_DECL: NodeType.FUNCTION_DEFINITION,
        CursorKind.TRANSLATION_UNIT: NodeType.MODULE,
        CursorKind.CLASS_DECL: NodeType.CLASS,
        CursorKind.STRUCT_DECL: NodeType.CLASS,
        CursorKind.PREPROCESSING_DIRECTIVE: NodeType.PREPROCESSING_DIRECTIVE,
    }

    def __init__(self):
        super().__init__()

    @classmethod
    def supported_extensions(cls) -> tuple[str]:
        return cls._PARSABLE_EXTENSIONS

    def _parse_nodes(self, nodes, allowed_include_paths) -> list:
        expanded_nodes = []

        extractions = {"signature": r"^\s*(?P<signature>.+)\s*{"}

        for node in nodes:
            signature = node.displayname

            if node.location.file is None:
                file_loc = node.displayname
            else:
                file_loc = node.location.file.name

            start_line = node.extent.start.line
            start_column = node.extent.start.column
            end_line = node.extent.end.line
            end_column = node.extent.end.column

            if node.kind == CursorKind.CXX_METHOD:
                access_specifier = node.access_specifier.name.lower()
                class_name = node.semantic_parent.displayname

            with open(file_loc, "r") as f:
                file_content = f.readlines()

            # Extract the extent of the text
            text = file_content[start_line - 1 : end_line]
            text[0] = text[0][start_column - 1 :]
            text[-1] = text[-1][:end_column]

            text = "".join(text).strip()

            node_type = self._mapped_node_type(node_type=node.kind)
            if node_type is None:
                continue

            if self._is_function_type(node.kind) or (
                node.kind == CursorKind.CLASS_DECL
            ):
                for extraction_name, extraction_exp in extractions.items():
                    match_obj = re.match(extraction_exp, text, flags=re.MULTILINE)
                    if match_obj is None:
                        # self._logger.error(f"No {extraction_name} found for {text}")
                        signature = node.displayname
                        # continue
                    else:
                        details = match_obj.groupdict()
                        if extraction_name == 'signature':
                            signature = details['signature']
            else:
                signature = node.displayname

            expanded_node = self.create_standard_node(
                type=node_type.name,
                signature=signature,
                text=text,
                file_loc=file_loc,
                includes=self._get_includes(node, allowed_include_paths),
                start_line=start_line,
                source=f"{os.path.basename(file_loc)} (line: {start_line}): {signature}",
            )

            expanded_node["end_line"] = end_line

            if node.kind == CursorKind.CXX_METHOD:
                expanded_node["access_specifier"] = access_specifier
                expanded_node["class"] = class_name

            expanded_nodes.append(expanded_node)

        return expanded_nodes

    def _get_includes(self, node, allowed_include_paths):
        include_files = []
        for include_obj in node.translation_unit.get_includes():
            if self._is_node_in_allowed_path(
                include_obj.include.name, allowed_include_paths
            ):
                include_files.append(include_obj.include.name)
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

    def _load_nodes_from_file(self, path, allowed_include_paths) -> list:
        nodes = []

        def traverse(node):
            if not self._is_node_in_allowed_path(node, allowed_include_paths):
                return

            for child in node.get_children():
                traverse(child)

            if self._mapped_node_type(node.kind) is None:
                return

            if self._is_function_type(node.kind) and (node.is_definition() is False):
                # Don't save off function declarations
                # Only keep definitions
                return
            
            if (node.kind == CursorKind.CLASS_DECL) and (node.is_definition() is False):
                # Don't save off forward class declarations
                # Only keep definitions
                return

            nodes.append(node)

        # clang.cindex.Config.set_library_path()
        index = clang.cindex.Index.create()

        tu = index.parse(path)

        root = tu.cursor
        traverse(root)

        return nodes

    def _parse_nodes_from_file(self, path, allowed_include_paths) -> list:
        nodes = self._load_nodes_from_file(
            path=path, allowed_include_paths=allowed_include_paths
        )
        parsed_nodes = self._parse_nodes(
            nodes=nodes, allowed_include_paths=allowed_include_paths
        )
        return parsed_nodes

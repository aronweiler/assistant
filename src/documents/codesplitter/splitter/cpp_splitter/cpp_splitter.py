
import glob
import json
import os

from documents.codesplitter.node_types import NodeType

from documents.codesplitter.splitter.splitter_base import SplitterBase

import clang.cindex
from clang.cindex import CursorKind


class CppSplitter(SplitterBase):

    _PARSABLE_EXTENSIONS = (
        '.c',
        '.cc',
        '.cpp',
        '.h',
        '.hh',
        '.hpp'
    )

    def __init__(self):
        super().__init__()


    @classmethod
    def supported_extensions(cls) -> tuple[str]:
        return cls._PARSABLE_EXTENSIONS
        

    def _parse_nodes(self, nodes) -> list:
        expanded_nodes = []
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

            with open(file_loc, 'r') as f:
                file_content = f.readlines()

            # Extract the extent of the text
            text = file_content[start_line-1:end_line]
            text[0] = text[0][start_column-1:]
            text[-1] = text[-1][:end_column]

            text = "".join(text).strip()

            type_map = {
                CursorKind.CXX_METHOD: NodeType.CLASS_METHOD,
                CursorKind.FUNCTION_DECL: NodeType.FUNCTION_DEFINITION,
                CursorKind.TRANSLATION_UNIT: NodeType.MODULE
            }

            try:
                node_type = type_map[node.kind]
            except:
                node_type = NodeType.UNKNOWN
                raise Exception(f"Node type {node.kind.name} is unmapped")

            expanded_node = {
                'type': node_type.name,
                'signature': signature,
                'text': text,
                'file_loc': file_loc,
                'includes': self._get_includes(node)
            }

            if node.kind == CursorKind.CXX_METHOD:
                expanded_node['access_specifier'] = access_specifier
                expanded_node['class'] = class_name

            expanded_nodes.append(expanded_node)

        return expanded_nodes

    @staticmethod
    def _get_includes(node):
        include_files = []
        for include_obj in node.translation_unit.get_includes():
            include_files.append(include_obj.include.name)
        return include_files


    @staticmethod
    def _find_nodes(path) -> list:

        NODE_KINDS_OF_INTEREST = (  
            CursorKind.CXX_METHOD,
            CursorKind.FUNCTION_DECL,
            CursorKind.TRANSLATION_UNIT
        )

        FUNCTION_KINDS = (
            CursorKind.CXX_METHOD,
            CursorKind.FUNCTION_DECL
        )

        nodes = []
   
        def traverse(node):

            for child in node.get_children():
                traverse(child)

            if node.kind in NODE_KINDS_OF_INTEREST: 

                if node.kind in FUNCTION_KINDS:

                    # Don't save off function declarations
                    # Only keep definitions
                    if node.is_definition() == False:
                        return

                nodes.append(node)


        #clang.cindex.Config.set_library_path()
        index = clang.cindex.Index.create()

        tu = index.parse(path)

        root = tu.cursor        
        traverse(root)

        return nodes


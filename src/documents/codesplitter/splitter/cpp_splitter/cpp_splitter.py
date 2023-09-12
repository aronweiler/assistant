
import os

from src.documents.codesplitter.node_types import NodeType

from src.documents.codesplitter.splitter.splitter_base import SplitterBase

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

    _FUNCTION_TYPES = (
        CursorKind.CXX_METHOD,
        CursorKind.FUNCTION_DECL
    )

    _GENERIC_NODE_TYPE_MAP = {
        CursorKind.CXX_METHOD: NodeType.CLASS_METHOD,
        CursorKind.FUNCTION_DECL: NodeType.FUNCTION_DEFINITION,
        CursorKind.TRANSLATION_UNIT: NodeType.MODULE,
        CursorKind.CLASS_DECL: NodeType.CLASS,
        CursorKind.STRUCT_DECL: NodeType.CLASS,
        CursorKind.PREPROCESSING_DIRECTIVE: NodeType.PREPROCESSING_DIRECTIVE,
        CursorKind.INCLUSION_DIRECTIVE: NodeType.INCLUDE,
    }

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

            node_type = self._mapped_node_type(node_type=node.kind)
            if node_type is None:
                continue

            expanded_node = {
                'type': node_type.name, # Standard
                'text': text, # Standard
                'file_loc': file_loc, # Standard
                'includes': self._get_includes(node),      
                'start_line': start_line, # Standard
                'end_line': end_line, 
                'signature': signature, # Standard
                'source': f"{os.path.basename(file_loc)} (line: {start_line}): {signature}", # Standard
            }

            if node.kind == CursorKind.CXX_METHOD:
                expanded_node['access_specifier'] = access_specifier
                expanded_node['class'] = class_name

            # This is accomplished by the 'signature' field
            # if node.kind in (CursorKind.CXX_METHOD, CursorKind.FUNCTION_DECL):
            #     expanded_node['func_name'] = signature

            expanded_nodes.append(expanded_node)

        return expanded_nodes


    def _get_includes(self, node):
        include_files = []
        for include_obj in node.translation_unit.get_includes():
            include_files.append(include_obj.include.name)
        return include_files


    def _load_nodes_from_file(self, path) -> list:

        nodes = []
   
        def traverse(node):

            for child in node.get_children():
                traverse(child)

            if self._mapped_node_type(node.kind) is None:
                return
            
            if self._is_function_type(node.kind) and (node.is_definition() is False):
                # Don't save off function declarations
                # Only keep definitions
                return

            nodes.append(node)


        #clang.cindex.Config.set_library_path()
        index = clang.cindex.Index.create()

        tu = index.parse(path)

        root = tu.cursor        
        traverse(root)

        return nodes


    def _parse_nodes_from_file(self, path) -> list:
        nodes = self._load_nodes_from_file(path=path)
        parsed_nodes = self._parse_nodes(nodes=nodes)
        return parsed_nodes

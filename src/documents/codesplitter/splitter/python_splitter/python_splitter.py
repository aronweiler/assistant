
import ast
import re

from src.documents.codesplitter.node_types import NodeType

from src.documents.codesplitter.splitter.splitter_base import SplitterBase


class PythonSplitter(SplitterBase):

    _PARSABLE_EXTENSIONS = (
        '.py',
    )

    _FUNCTION_TYPES = (
        ast.FunctionDef,
    )

    _GENERIC_NODE_TYPE_MAP = {
        ast.FunctionDef: NodeType.FUNCTION_DEFINITION,
        ast.Import: NodeType.INCLUDE,
        ast.Module: NodeType.MODULE,
        ast.ClassDef: NodeType.CLASS
    }

    def __init__(self):
        super().__init__()


    @classmethod
    def supported_extensions(cls) -> tuple[str]:
        return cls._PARSABLE_EXTENSIONS
           

    def _parse_nodes(self, nodes) -> list:
        expanded_nodes = []
        
        extractions = {
            'func_name': r'^\s*def\s+(?P<func_name>\w+)\(.*\).*:',
            'signature': r'^\s*def\s+(?P<signature>.+):'
        }
        
        # return expanded_nodes
        for node in nodes:

            file_loc = node['metadata']['source_path']

            node_type = self._mapped_node_type(type(node['node']))

            if node_type is None:
                self._logger.debug(f"Node type {node['node'].__class__.__name__} is unmapped")
                continue
            
            text = None
            if self._is_function_type(type(node['node'])): # in (NodeType.CLASS_METHOD, NodeType.FUNCTION_DEFINITION):
                with open(file_loc, 'r') as f:
                    text = ast.get_source_segment(
                        source=f.read(),
                        node=node['node']
                    )

                    for extraction_name, extraction_exp in extractions.items():
                        match_obj = re.match(extraction_exp, text)
                        details = match_obj.groupdict()
                        node['metadata'][extraction_name] = details[extraction_name]
            
            expanded_node = {
                'type': node_type.name,
                'text': text,
                'file_loc': file_loc
            }

            if 'signature' in node['metadata']:
                expanded_node['signature'] = node['metadata']['signature']

            if 'func_name' in node['metadata']:
                expanded_node['func_name'] = node['metadata']['func_name']

            if 'includes' in node['metadata']:
                expanded_node['includes'] = node['metadata']['includes']

            if 'class' in node['metadata']:
                expanded_node['class'] = node['metadata']['class']

                # Override a function into a class method if there is a class associated with it
                expanded_node['type'] = NodeType.CLASS_METHOD.name


            expanded_nodes.append(expanded_node)

        return expanded_nodes


    def _find_nodes(self, path) -> list:

        imports = []
        functions = []
        class_methods = []
        classes = []
        current_class = None

        nodes = []
   
        with open(path, 'r') as f:
            tree = ast.parse(source=f.read())

        for node in ast.walk(tree):

            if type(node) in (ast.Import, ast.ImportFrom):
                imports.append(node)
                continue

            if type(node) == ast.ClassDef:
                current_class = node.name
                classes.append(
                    {
                        'node': node,
                        'metadata': {}
                    }
                )
                continue

            if type(node) == ast.FunctionDef:
                if current_class is None:
                    functions.append(
                        {
                            'node': node,
                            'metadata': {}
                        }
                    )
                else:
                    class_methods.append(
                        {
                            'node': node,
                            'metadata': {
                                'class': current_class,
                            }
                        }
                    )

        # Combine various node types
        nodes.extend(class_methods)
        nodes.extend(functions)
        nodes.extend(classes)

        # Generate list of imports
        import_names = []
        for import_obj in imports:
            import_names.append(import_obj.names[0].name)

        for node in nodes:
            node['metadata']['source_path'] = path
            node['metadata']['includes'] = import_names

        return nodes
    

    def _parse_nodes_from_file(self, path) -> list:
        nodes = self._find_nodes(path=path)
        parsed_nodes = self._parse_nodes(nodes=nodes)
        return parsed_nodes

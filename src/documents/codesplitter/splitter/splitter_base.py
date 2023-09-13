

import abc
import glob
import logging
import os

from src.documents.codesplitter.node_types import NodeType


class SplitterBase(abc.ABC):

    def __init__(self):
        self._logger = logging.getLogger(__name__)


    def _get_supported_files(self, path: str):
        files = []

        if os.path.isfile(path):
            if os.path.splitext(path)[1] in self.supported_extensions():
                return [path]
            else:
                return []
            
        search_path_exp = os.path.join(path,"**","*")
        for file_loc in glob.glob(search_path_exp, recursive=True):
            if os.path.splitext(file_loc)[1] in self.supported_extensions():
                files.append(file_loc)
        
        return files
    

    @abc.abstractclassmethod
    def supported_extensions(cls) -> tuple[str]:
        return tuple()
        

    @abc.abstractmethod
    def _parse_nodes_from_file(self, path) -> list:
        return []
    

    def _is_function_type(self, node_type) -> bool:
        if node_type in self._FUNCTION_TYPES:
            return True
        
        return False
    
    def _mapped_node_type(self, node_type) -> NodeType:
        return self._GENERIC_NODE_TYPE_MAP.get(node_type, None)
    

    def parse(self, path) -> list[dict]:
        files = self._get_supported_files(path=path)

        combined_nodes = []
        for file in files:
            self._logger.info(f"Parsing {file}")
            nodes = self._parse_nodes_from_file(path=file)
            combined_nodes.extend(nodes)

        return combined_nodes
    
    @staticmethod
    def create_standard_node(
        type: NodeType,
        signature: str,
        text: str,
        file_loc: str,
        includes: list[str],
        start_line: int,
        source: str
    ) -> dict:
        return {
            'type': type,
            'signature': signature,
            'text': text,
            'file_loc': file_loc,
            'includes': includes,
            'start_line': start_line,
            'source': source
        }
        



import abc
import glob
import logging
import os


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
        

    @abc.abstractstaticmethod
    def _find_nodes(path) -> list:
        return []
    

    @abc.abstractmethod
    def _parse_nodes(self, nodes) -> list:
        return []


    def parse(self, path) -> list[dict]:
        files = self._get_supported_files(path=path)

        transformed_nodes_list = []
        for file in files:
            self._logger.info(f"Parsing {file}")
            nodes = self._find_nodes(file)
            transformed_nodes = self._parse_nodes(nodes)
            transformed_nodes_list.extend(transformed_nodes)

        return transformed_nodes_list

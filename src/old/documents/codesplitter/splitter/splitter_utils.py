
import logging
import os

from src.documents.codesplitter.splitter.splitter_base import SplitterBase
from src.documents.codesplitter.splitter.cpp.cpp_splitter import CppSplitter
from src.documents.codesplitter.splitter.python.python_splitter import PythonSplitter

logger = logging.getLogger(__name__)


SPLITTERS = {
    'cpp': CppSplitter,
    'python': PythonSplitter
}


def get_splitter(source_path: str, hint: str) -> SplitterBase | None:   

    splitter = None

    if hint in SPLITTERS.keys():
        splitter = SPLITTERS[hint]()
        logger.info(f"Using splitter {hint}")
        return splitter
    
    for splitter_lang, splitter_class in SPLITTERS.items():
        supported_extensions = splitter_class().supported_extensions()
        if os.path.splitext(source_path)[1] in supported_extensions:    
            logger.info(f"Using splitter {splitter_lang}")
            splitter = splitter_class()

    return splitter


def get_splitter_groupings(file_types: list[str]):
    groups = {
        'unsupported_extensions': []
    }
    for file_type in file_types:
        file_type_supported = False
        for splitter_lang, splitter_class in SPLITTERS.items():
            supported_extensions = splitter_class().supported_extensions()
            if file_type in supported_extensions:
                if splitter_lang not in groups:
                    groups[splitter_lang] = {
                        'splitter_class': splitter_class,
                        'supported_extensions': []
                    }
                
                groups[splitter_lang]['supported_extensions'].append(file_type)
                file_type_supported = True
        
        if file_type_supported is False:
            groups['unsupported_extensions'].append(file_type)

    return groups
                

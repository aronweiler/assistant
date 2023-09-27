import glob
import json
import logging
import os


from src.documents.codesplitter.node_types import NodeType


logger = logging.getLogger(__name__)


def pretty_print(data):
    print(json.dumps(data, indent=4))


def get_file_extensions_in_path(path: str) -> list[str]:
    def _get_file_extension(file_loc: str) -> str:
        return os.path.splitext(file_loc)[1].lower()

    discovered_extensions = {}

    # For single file use-case
    if os.path.isfile(path):
        file_extension = _get_file_extension(file_loc=path)
        discovered_extensions[file_extension] = [path]
        return discovered_extensions

    search_path_exp = os.path.join(path, "**", "*")
    for file_loc in glob.glob(search_path_exp, recursive=True):
        file_extension = _get_file_extension(file_loc=file_loc)
        if file_extension not in discovered_extensions:
            discovered_extensions[file_extension] = []

        discovered_extensions[file_extension].append(file_loc)

    return discovered_extensions


def node_stats(nodes: list):
    num_nodes = 0
    node_types = {node_type.name: 0 for node_type in NodeType}

    for node in nodes:
        num_nodes += 1
        node_types[node["type"]] += 1

    return {"total_nodes": num_nodes, "node_types": node_types}

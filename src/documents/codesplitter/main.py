
import argparse
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import src.documents.codesplitter.utils as utils

import src.documents.codesplitter.splitter.splitter_utils as splitter_utils


#logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)


def handle_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--language-mode',
        type=str,
        choices=[
            'auto',
            'cpp'
        ],
        default='auto'
    )

    parser.add_argument(
        '--path',
        type=str,
        required=True
    )

    args = parser.parse_args()
    return args


def main(args):
    run(path=args.path)

def run(path):

    files = utils.get_file_extensions_in_path(path=path)
    
    file_types = list(files.keys())
    logger.info(f"Found the following file types: {file_types}")

    splitter_groups = splitter_utils.get_splitter_groupings(file_types=file_types)
    logger.info(f"File splitter groups:\n{splitter_groups}")

    all_nodes = []

    for splitter_lang in splitter_groups.keys():
        if splitter_lang == 'unsupported_extensions':
            continue

        splitter = splitter_utils.get_splitter(
            source_path=None,
            hint=splitter_lang
        )

        if splitter is None:
            raise Exception(f"No splitter found")
    
        nodes = splitter.parse(path)

        node_stats = utils.node_stats(nodes=nodes)
        utils.pretty_print(node_stats)

        all_nodes.extend(nodes)
        
    return all_nodes

if __name__ == "__main__":
    run("/Repos/assistant/streamlit_ui.py")
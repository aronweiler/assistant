from ast import List
import os
import sys
import logging
from github import Github

from github.ContentFile import ContentFile

from src.integrations.shared import TEXT_BASED_EXTENSIONS, is_text_based_extension


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.integrations.github import github_shared


def get_text_based_files_from_repo(
    github_client: Github, repository_name: str, branch_name: str
):
    # Get the repository
    repository = github_client.get_repo(repository_name)

    # Get the git tree
    git_tree = repository.get_git_tree(sha=branch_name, recursive=True).tree

    # Filter out text-based files from the tree
    matching_files = [
        item
        for item in git_tree
        if item.type == "blob" and is_text_based_extension(item.path)
    ]

    return matching_files

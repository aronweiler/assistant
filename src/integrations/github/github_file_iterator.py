from ast import List
import os
import sys
import logging
from github import Github

from github.ContentFile import ContentFile


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.integrations.github import github_shared

# Define a set of file extensions that are considered text-based
CODE_FILE_EXTENSIONS = [
    ".py",  # Python
    ".js",  # JavaScript
    ".html",  # HTML
    ".css",  # Cascading Style Sheets
    ".java",  # Java
    ".c",  # C
    ".cpp",  # C++
    ".cs",  # C#
    ".rb",  # Ruby
    ".php",  # PHP
    ".ts",  # TypeScript
    ".swift",  # Swift
    ".go",  # Go
    ".rs",  # Rust
    ".kt",  # Kotlin
    ".m",  # Objective-C
    ".sh",  # Shell script
    ".bat",  # Batch file (Windows)
    ".pl",  # Perl
    ".scala",  # Scala
    ".groovy",  # Groovy
    ".lua",  # Lua
    # Markup and data formats:
    ".xml",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".md",  # Markdown
    ".rst",  # reStructuredText
    ".tex",  # TeX
    ".toml",  # TOML
    ".ini",  # INI
    ".cfg",  # Configuration file
    ".conf",  # Configuration file
    ".properties",  # Properties file
    # Configuration files:
    "Dockerfile",
    "Makefile",
    "Jenkinsfile",
    "Vagrantfile",
    ".txt",  # Text file
    ".log",  # Log file
    ".sql",  # SQL script
    ".r",  # R script
    # Note that 'CMakeLists.txt' is not an extension but a specific filename.
    # If you want to include it, you'll need to handle it separately in your logic.
    # Scripting and templating languages:
    ".ps1",  # PowerShell script
    # Template files can have various extensions; here are some examples:
    ".tmpl",
    ".tpl",
    ".template",
]


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


def is_text_based_extension(file_path: str):
    # Extract the file extension and check if it's in our set of text-based extensions
    _, extension = os.path.splitext(file_path)

    return extension.lower() in CODE_FILE_EXTENSIONS


if __name__ == "__main__":
    # Example usage
    repository_name = "aronweiler/assistant"

    # Get the SOURCE_CONTROL_PAT from the environment
    source_control_pat = os.environ["SOURCE_CONTROL_PAT"]

    # Retrieve the Github client using your source control PAT
    github_client = github_shared.retrieve_github_client(source_control_pat)

    matching_files = get_text_based_files_from_repo(
        repository_name=repository_name,
        branch_name="main",
        github_client=github_client,
    )

    for file in matching_files:
        print(file.path)

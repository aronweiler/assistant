import os
import sys


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.integrations.github import github_shared


class GitHubFileIterator:
    def __init__(self, repository_name, file_extensions, source_control_pat):
        self.repository_name = repository_name
        self.file_extensions = file_extensions
        self.source_control_pat = source_control_pat

    def get_matching_files(self):
        # Retrieve the Github client using your source control PAT
        github_client = github_shared.retrieve_github_client(self.source_control_pat)

        # Get the repository
        repository = github_client.get_repo(self.repository_name)

        matching_files = []

        # Iterate through all files in all directories
        contents = repository.get_contents("")
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repository.get_contents(file_content.path))
            else:
                if any(file_content.name.endswith(ext) for ext in self.file_extensions):
                    matching_files.append(file_content.download_url)

        return matching_files


if __name__ == "__main__":
    # Example usage
    repository_name = "aronweiler/assistant"
    file_extensions = [".py", ".txt"]  # Specify your desired file extensions here

    # Get the SOURCE_CONTROL_PAT from the environment
    source_control_pat = os.environ["SOURCE_CONTROL_PAT"]

    iterator = GitHubFileIterator(repository_name, file_extensions, source_control_pat)
    matching_files = iterator.get_matching_files()

    for url in matching_files:
        print(url)

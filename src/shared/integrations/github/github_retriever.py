import logging
import os
import re
import sys


# Append the root directory of the project to the system path for module importing.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Import shared GitHub integration utilities.
from src.shared.integrations.github import github_file_iterator
import src.shared.integrations.github.github_shared as github_shared


class GitHubRetriever:
    def __init__(self, source_control_url, source_control_pat, requires_authentication=False):
        # Initialize a logger instance for this class.
        self._logger = logging.getLogger(__name__)
        # Store the base URL for the source control (GitHub).
        self._source_control_url = source_control_url
        # Retrieve a GitHub client using the provided personal access token (PAT).
        self._gh = github_shared.retrieve_github_client(
            source_control_pat=source_control_pat,
            source_control_url=source_control_url,
            requires_authentication=requires_authentication,
        )

    def retrieve_branches(self, url):
        # Parse the URL to extract repository information.
        url_info = github_shared.parse_url(url=url, client=self._gh)

        # Extract the repository path from the URL info dictionary.
        repo_path = url_info["repo_path"]

        try:
            # Attempt to get the repository object from GitHub.
            repo = self._gh.get_repo(repo_path)
        except Exception as ex:
            # If there's an error, raise an exception with a custom message.
            raise Exception(f"Failed to retrieve repo {url} from server")

        # Get all branches from the repository object.
        branches = repo.get_branches()

        # Return a list of branch names extracted from branch objects.
        return [b.name for b in branches]
    
    def scan_repository(self, url, branch_name):
        # Parse the URL to extract repository information.
        url_info = github_shared.parse_url(url=url, client=self._gh)

        # Extract the repository path from the URL info dictionary.
        repo_path = url_info["repo_path"]

        return github_file_iterator.get_text_based_files_from_repo(self._gh, repository_name=repo_path, branch_name=branch_name)

    def retrieve_data(self, url):
        # Parse the URL to determine if it's pointing to a file or a pull request (diff).
        url_info = github_shared.parse_url(url=url, client=self._gh)

        # Depending on the type of content pointed by URL, call appropriate retrieval method.
        if url_info["type"] == "file":
            return self._retrieve_file_data(url=url)
        elif url_info["type"] == "diff":
            return self._retrieve_pull_request_data(url=url)
        
    def retrieve_code(self, path: str, repo_address:str, branch_name: str) -> str:
        url = f"{repo_address}/blob/{branch_name}/{path}"
        
        # Parse the URL to extract file and repository information.
        return self._retrieve_file_data(url=url)

    def _retrieve_file_data(self, url):
        # Parse the URL to extract file and repository information.
        url_info = github_shared.parse_url(url=url, client=self._gh)

        domain = url_info["domain"]

        # Check if domain matches authorized instance; raise exception if not.
        if domain not in self._source_control_url:
            raise Exception(
                f"URL domain ({domain}) is different than authorized instance ({self._source_control_url})"
            )

        repo_path = url_info["repo_path"]

        try:
            # Attempt to get the repository object from GitHub using its path.
            repo = self._gh.get_repo(repo_path)
        except Exception as ex:
            raise Exception(f"Failed to retrieve repo {repo_path} from server")

        ref = url_info["ref"]

        file_path = url_info["file_path"]

        # Retrieve file contents from GitHub given its path and reference (branch/tag/commit).
        f = repo.get_contents(file_path, ref=ref)

        file_content = f.decoded_content.decode("UTF-8")

        # Return a dictionary containing various details about the file retrieved.
        return {
            "type": "file",
            "project_id": "N/A",
            "url": url,
            "ref": ref,
            "file_path": file_path,
            "file_content": file_content,
            "repo_path": repo_path,
        }

    def _retrieve_pull_request_data(self, url):
         # Parse the URL to extract pull request and repository information.
        url_info = github_shared.parse_url(url=url, client=self._gh)

        if url_info["domain"] not in self._source_control_url:
            raise Exception(
                f"URL domain ({url_info['domain']}) is different than authorized instance ({self._source_control_url})"
            )

        repo_path = url_info["repo_path"]
        pull_request_id = url_info["pull_request_id"]

        try:
            repo = self._gh.get_repo(repo_path)
        except Exception as ex:
            raise Exception(f"Failed to retrieve repo {repo_path} from server")

        pull_request = repo.get_pull(number=int(pull_request_id))

        changes = pull_request.get_files()
        changes2 = []
        for change in changes:
            diff = change.patch
            diff_split = diff.splitlines()
            diff2 = {"old": [], "new": []}

            for line in diff_split:
                if line.startswith("-"):
                    diff2["old"].append(line.lstrip("-"))
                elif line.startswith("+"):
                    diff2["new"].append(line.lstrip("+"))
                elif line.startswith("@"):
                    pass
                elif line.startswith("\\"):
                    pass
                else:
                    diff2["new"].append(line)
                    diff2["old"].append(line)

            diff2["old"] = "\n".join(diff2["old"])
            diff2["new"] = "\n".join(diff2["new"])
            diff2["raw"] = diff
            diff2["old_path"] = change.previous_filename
            diff2["new_path"] = change.filename
            changes2.append(diff2)

        return {
            "type": "diff",
            "id": pull_request_id,
            "title": pull_request.title,
            "description": pull_request.body,
            "created_at": pull_request.created_at,
            "url": url,
            "changes": changes2,
        }
        
if __name__ == "__main__":
   
    # Create an instance of GitHubRetriever.
    gr = GitHubRetriever(
        source_control_url="https://api.github.com",
        source_control_pat="xxx",
        requires_authentication=True,
    )

    # Retrieve branches from a repository.
    branches = gr.retrieve_branches(url="https://github.com/aronweiler/assistant")
    
    print(branches)
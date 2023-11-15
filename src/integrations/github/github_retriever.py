import logging
import os
import re
import sys

import dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import src.integrations.github.github_shared as github_shared


class GitHubRetriever:
    def __init__(self, source_control_url, source_control_pat):
        self._logger = logging.getLogger(__name__)
        self._source_control_url = source_control_url
        self._gh = github_shared.retrieve_github_client(
            source_control_url=source_control_url, source_control_pat=source_control_pat
        )

    def retrieve_data(self, url):
        url_info = github_shared.parse_url(url=url)

        if url_info["type"] == "file":
            return self.retrieve_file_data(url=url)
        elif url_info["type"] == "diff":
            return self.retrieve_pull_request_data(url=url)

    def retrieve_file_data(self, url):
        url_info = github_shared.parse_url(url=url)

        domain = url_info["domain"]
        if domain not in self._source_control_url:
            raise Exception(
                f"URL domain ({domain}) is different than authorized instance ({self._source_control_url})"
            )

        repo_path = url_info["repo_path"]

        try:
            repo = self._gh.get_repo(repo_path)
        except Exception as ex:
            raise Exception(f"Failed to retrieve repo {repo_path} from server")

        ref = url_info["ref"]
        file_path = url_info["file_path"]

        f = repo.get_contents(file_path, ref=ref)

        file_content = f.decoded_content.decode("UTF-8")

        return {
            "type": "file",
            "project_id": "N/A",
            "url": url,
            "ref": ref,
            "file_path": file_path,
            "file_content": file_content,
        }

    def retrieve_pull_request_data(self, url):
        url_info = github_shared.parse_url(url=url)

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
    dotenv.load_dotenv()
    file_retriever = GitHubRetriever(
        source_control_url=os.getenv("source_control_url"),
        source_control_pat=os.getenv("source_control_pat"),
    )

    file_data = file_retriever.retrieve_file_data(url="")

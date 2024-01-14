import logging
import os
import re
import sys

import dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import src.integrations.gitlab.gitlab_shared as gitlab_shared


class GitlabRetriever:
    def __init__(self, source_control_url, source_control_pat, requires_authentication=False):
        self._logger = logging.getLogger(__name__)
        self._source_control_url = source_control_url
        self._source_control_pat = source_control_pat
        self._gl = gitlab_shared.retrieve_gitlab_client(
            source_control_url=source_control_url,
            source_control_pat=source_control_pat,
            requires_authentication=requires_authentication,
        )

    def retrieve_data(self, url):
        url_info = gitlab_shared.parse_url(client=self._gl, url=url)

        if url_info["type"] == "file":
            return self.retrieve_file_data(url=url)
        elif url_info["type"] == "diff":
            return self.retrieve_merge_request_data(url=url)
        elif url_info["type"] == "repo":
            return self.retrieve_repo_data(url=url)

    def retrieve_repo_data(self, url):
        url_info = gitlab_shared.parse_url(client=self._gl, url=url)

        if url_info["domain"] not in self._source_control_url:
            raise Exception(
                f"URL domain ({url_info['domain']}) is different than authorized instance ({self._source_control_url})"
            )

        try:
            project = self._gl.projects.get(url_info["project_id"])
        except Exception as ex:
            raise Exception(
                f"Failed to retrieve project {url_info['repo_path']} ({url_info['project_id']}) from server"
            )

        return {
            "type": "repo",
            "project_id": url_info["project_id"],
            "url": url,
            "repo_path": url_info["repo_path"],
            "project": project,
        }

    def retrieve_file_data(self, url):
        url_info = gitlab_shared.parse_url(client=self._gl, url=url)

        if url_info["domain"] not in self._source_control_url:
            raise Exception(
                f"URL domain ({url_info['domain']}) is different than authorized instance ({self._source_control_url})"
            )

        try:
            project = self._gl.projects.get(url_info["project_id"])
        except Exception as ex:
            raise Exception(
                f"Failed to retrieve project {url_info['repo_path']} ({url_info['project_id']}) from server"
            )

        f = project.files.get(file_path=url_info["file_path"], ref=url_info["ref"])

        file_content = f.decode().decode("UTF-8")

        return {
            "type": "file",
            "project_id": url_info["project_id"],
            "url": url,
            "ref": url_info["ref"],
            "file_path": url_info["file_path"],
            "file_content": file_content,
        }

    def retrieve_merge_request_data(self, url):
        url_info = gitlab_shared.parse_url(client=self._gl, url=url)

        if url_info["domain"] not in self._source_control_url:
            raise Exception(
                f"URL domain ({url_info['domain']}) is different than authorized instance ({self._source_control_url})"
            )

        try:
            project = self._gl.projects.get(url_info["project_id"])
        except Exception as ex:
            raise Exception(
                f"Failed to retrieve project {url_info['repo_path']} ({url_info['project_id']}) from server"
            )

        merge_request = project.mergerequests.get(id=url_info["merge_request_iid"])

        changes = merge_request.changes()["changes"]
        changes2 = []
        for change in changes:
            diff = change["diff"]
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
            diff2["old_path"] = change["old_path"]
            diff2["new_path"] = change["new_path"]
            changes2.append(diff2)

        return {
            "type": "diff",
            "project_id": url_info["project_id"],
            "mr_iid": merge_request.iid,
            "title": merge_request.title,
            "description": merge_request.description,
            "created_at": merge_request.created_at,
            "url": merge_request.web_url,
            "changes": changes2,
        }


if __name__ == "__main__":
    dotenv.load_dotenv()
    file_retriever = GitlabRetriever(
        source_control_url=os.getenv("SOURCE_CONTROL_URL"),
        source_control_pat=os.getenv("SOURCE_CONTROL_PAT"),
    )

    file_data = file_retriever.retrieve_file_data(url="")

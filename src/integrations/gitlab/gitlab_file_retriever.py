import logging
import os
import re
import sys

import dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import src.integrations.gitlab.gitlab_shared as gitlab_shared


class GitlabFileRetriever:
    def __init__(self, source_control_url, source_control_pat):
        self._logger = logging.getLogger(__name__)
        self._source_control_url = source_control_url
        self._gl = gitlab_shared.retrieve_gitlab_client(
            source_control_url=source_control_url,
            source_control_pat=source_control_pat,
            verify_auth=True,
        )

    def retrieve_file_data(self, url):
        url_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)/-/blob/(?P<ref>[a-zA-Z0-9\.\-\_]+)/(?P<file_path>.*)"
        match_obj = re.match(pattern=url_re, string=url)

        if match_obj is None:
            raise Exception(f"Failed to URL match against {url}")

        details = match_obj.groupdict()
        for field in ("domain", "repo_path", "ref", "file_path"):
            if field not in details:
                raise Exception(f"Unable to match {field} in {url}")

        domain = details["domain"]
        if domain not in self._source_control_url:
            raise Exception(
                f"URL domain ({domain}) is different than authorized instance ({self._source_control_url})"
            )

        repo_path = details["repo_path"]

        try:
            project = self._gl.projects.get(repo_path)
        except Exception as ex:
            raise Exception(f"Failed to retrieve project {repo_path} from server")

        ref = details["ref"]
        file_path = details["file_path"]

        f = project.files.get(file_path=file_path, ref=ref)

        file_content = f.decode().decode("UTF-8")

        return {
            "project_id": project.get_id(),
            "url": url,
            "ref": ref,
            "file_path": file_path,
            "file_content": file_content,
        }


if __name__ == "__main__":
    dotenv.load_dotenv()
    file_retriever = GitlabFileRetriever(
        source_control_url=os.getenv("SOURCE_CONTROL_URL"),
        source_control_pat=os.getenv("SOURCE_CONTROL_PAT"),
    )

    file_data = file_retriever.retrieve_file_data(url="")

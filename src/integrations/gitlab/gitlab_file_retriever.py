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
        url_info = gitlab_shared.parse_url(
            client=self._gl,
            url=url
        )

        if url_info['domain'] not in self._source_control_url:
            raise Exception(
                f"URL domain ({url_info['domain']}) is different than authorized instance ({self._source_control_url})"
            )

        try:
            project = self._gl.projects.get(url_info['project_id'])
        except Exception as ex:
            raise Exception(f"Failed to retrieve project {url_info['repo_path']} ({url_info['project_id']}) from server")
        
        f = project.files.get(
            file_path=url_info['file_path'],
            ref=url_info['ref']
        )

        file_content = f.decode().decode("UTF-8")

        return {
            "project_id": url_info['project_id'],
            "url": url,
            "ref": url_info['ref'],
            "file_path": url_info['file_path'],
            "file_content": file_content,
        }


if __name__ == "__main__":
    dotenv.load_dotenv()
    file_retriever = GitlabFileRetriever(
        source_control_url=os.getenv("SOURCE_CONTROL_URL"),
        source_control_pat=os.getenv("SOURCE_CONTROL_PAT"),
    )

    file_data = file_retriever.retrieve_file_data(url="")

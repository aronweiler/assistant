import logging
import os
import re
import sys

import dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import src.integrations.gitlab.gitlab_shared as gitlab_shared


class GitlabMergeRequestRetriever:
    def __init__(self, source_control_url, source_control_pat):
        self._logger = logging.getLogger(__name__)
        self._source_control_url = source_control_url
        self._source_control_pat = source_control_pat
        self._gl = gitlab_shared.retrieve_gitlab_client(
            source_control_url=source_control_url,
            source_control_pat=source_control_pat,
            verify_auth=True,
        )


    def retrieve_merge_request_data(self, url):
        url_info = gitlab_shared.parse_merge_request_url(
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
       
        merge_request = project.mergerequests.get(id=url_info['merge_request_iid'])
        
        for diff in merge_request.diffs.list():
            print(diff)
        
        return {
            # 'metadata': {
            #     'iid': previous_issue.iid,
            #     'title': previous_issue.title,
            #     'description': previous_issue.description,
            #     'created_at': previous_issue.created_at,
            #     'url': previous_issue.web_url,
            # },
            # 'findings': {}
        }



if __name__ == "__main__":
    dotenv.load_dotenv()
    retriever = GitlabMergeRequestRetriever(
        source_control_url=os.getenv("SOURCE_CONTROL_URL"),
        source_control_pat=os.getenv("SOURCE_CONTROL_PAT"),
    )

    data = retriever.retrieve_merge_request_data(url="https://code.medtronic.com/Ventilation/sandbox/llm-integration-prototypes/-/merge_requests/1")

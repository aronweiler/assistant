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
        
        changes = merge_request.changes()['changes']
        changes2 = []
        for change in changes:
            diff = change['diff']
            diff = diff.splitlines()
            diff2 = {
                'old': [],
                'new': []
            }

            for line in diff:
                if line.startswith('-'):
                    diff2['old'].append(line.lstrip('-'))
                elif line.startswith('+'):
                    diff2['new'].append(line.lstrip('+'))
                elif line.startswith('@'):
                    pass
                elif line.startswith('\\'):
                    pass
                else:
                    raise Exception(f"Diff parsing -> Unexpected character {line[0]} found. Expected '+, -, or @'.")
                
            changes2.append(diff2)
        
        return {
            'metadata': {
                'iid': merge_request.iid,
                'title': merge_request.title,
                'description': merge_request.description,
                'created_at': merge_request.created_at,
                'url': merge_request.web_url,
            },
            'changes': changes2
        }



if __name__ == "__main__":
    dotenv.load_dotenv()
    retriever = GitlabMergeRequestRetriever(
        source_control_url=os.getenv("SOURCE_CONTROL_URL"),
        source_control_pat=os.getenv("SOURCE_CONTROL_PAT"),
    )

    data = retriever.retrieve_merge_request_data(url="")

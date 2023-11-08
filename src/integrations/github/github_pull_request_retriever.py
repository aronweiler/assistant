import logging
import os
import re
import sys

import dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import src.integrations.github.github_shared as github_shared


class GitHubPullRequestRetriever:
    def __init__(self, source_control_url, source_control_pat):
        self._logger = logging.getLogger(__name__)
        self._source_control_url = source_control_url
        self._source_control_pat = source_control_pat
        self._gh = github_shared.retrieve_github_client(
            source_control_url=source_control_url,
            source_control_pat=source_control_pat
        )


    def retrieve_pull_request_data(self, url):
        url_info = github_shared.parse_pull_request_url(
            client=self._gh,
            url=url
        )

        if url_info['domain'] not in self._source_control_url:
            raise Exception(
                f"URL domain ({url_info['domain']}) is different than authorized instance ({self._source_control_url})"
            )

        try:
            project = self._gh.projects.get(url_info['project_id'])
        except Exception as ex:
            raise Exception(f"Failed to retrieve project {url_info['repo_path']} ({url_info['project_id']}) from server")
       
        pull_request = project.pulls.get(id=url_info['pull_request_id'])
        
        changes = pull_request.changes()['changes']
        changes2 = []
        for change in changes:
            diff = change['diff']
            diff_split = diff.splitlines()
            diff2 = {
                'old': [],
                'new': []
            }

            for line in diff_split:
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
            
            diff2['old'] = '\n'.join(diff2['old'])
            diff2['new'] = '\n'.join(diff2['new'])
            diff2['raw'] = diff
            changes2.append(diff2)
        
        return {
            'metadata': {
                'id': pull_request.iid,
                'title': pull_request.title,
                'description': pull_request.description,
                'created_at': pull_request.created_at,
                'url': pull_request.web_url,
            },
            'changes': changes2
        }



if __name__ == "__main__":
    dotenv.load_dotenv()
    retriever = GitHubPullRequestRetriever(
        source_control_url=os.getenv("SOURCE_CONTROL_URL"),
        source_control_pat=os.getenv("SOURCE_CONTROL_PAT"),
    )

    data = retriever.retrieve_pull_request_data(url="")

import logging
import os
import re
import sys

import dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import src.integrations.gitlab.gitlab_shared as gitlab_shared


class GitlabIssueRetriever:
    def __init__(self, source_control_url, source_control_pat):
        self._logger = logging.getLogger(__name__)
        self._source_control_url = source_control_url
        self._gl = gitlab_shared.retrieve_gitlab_client(
            source_control_url=source_control_url,
            source_control_pat=source_control_pat,
            verify_auth=True,
        )


    @staticmethod
    def _get_ref_from_title(title: str):
        pattern = r".*\(ref:\s+(?P<ref>.*)\).*"
        match_obj = re.match(pattern=pattern, string=title)

        if match_obj is None:
            return None
        
        details = match_obj.groupdict()
        if 'ref' not in details:
            return None
        
        return details['ref']
    

    def retrieve_issue_data(self, url):
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
       
        project_issues = project.issues.list()

        # Filter through all the project issues
        matching_issues = []
        for issue in project_issues:

            # Reviewer should be on a label
            if gitlab_shared.REVIEWER not in issue.labels:
                continue

            # Match the file path to the title
            if url_info['file_path'] not in issue.title:
                continue

            # Match the ref (branch/tag)
            if url_info['ref'] != self._get_ref_from_title(title=issue.title):
                continue

            # Issue must be in open state
            if issue.state not in ("opened","reopened"):
                continue
            
            matching_issues.append(issue)

        if len(matching_issues) == 0:
            return None
                
        # Sort the issues by IID (in descending order) so that the newest issue is first
        sorted_issues = sorted(matching_issues, key=lambda issue: issue.iid, reverse=True)

        previous_issue = sorted_issues[0]
        
        return {
            'metadata': {
                'iid': previous_issue.iid,
                'title': previous_issue.title,
                'description': previous_issue.description,
                'created_at': previous_issue.created_at,
                'url': previous_issue.web_url,
            },
            # 'issue_obj': previous_issue
        }



if __name__ == "__main__":
    dotenv.load_dotenv()
    issue_retriever = GitlabIssueRetriever(
        source_control_url=os.getenv("SOURCE_CONTROL_URL"),
        source_control_pat=os.getenv("SOURCE_CONTROL_PAT"),
    )

    issue_data = issue_retriever.retrieve_issue_data(url="")

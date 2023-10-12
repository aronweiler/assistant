
import logging
import os
import re
import sys

import dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import src.integrations.github.github_shared as github_shared


class GitHubFileRetriever:

    def __init__(self, source_control_url, source_control_pat):
        self._logger = logging.getLogger(__name__)
        self._source_control_url = source_control_url
        self._gh = github_shared.retrieve_github_client(
            source_control_url=source_control_url,
            source_control_pat=source_control_pat
        )

    
    def retrieve_file_data(self, url):
        url_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)/blob/(?P<ref>[a-zA-Z0-9\.\-\_]+)/(?P<file_path>.*)"
        match_obj = re.match(
            pattern=url_re,
            string=url
        )

        if match_obj is None:
            raise Exception(f"Failed to URL match against {url}")
    
        details = match_obj.groupdict()
        for field in ('domain', 'repo_path', 'ref', 'file_path'):
            if field not in details:
                raise Exception(f"Unable to match {field} in {url}")
            
        domain = details['domain']
        if domain not in self._source_control_url:
            raise Exception(f"URL domain ({domain}) is different than authorized instance ({self._source_control_url})")
        
        repo_path = details['repo_path']

        try:
            repo = self._gh.get_repo(repo_path)            
        except Exception as ex:
            raise Exception(f"Failed to retrieve project {repo_path} from server")

        ref = details['ref']
        file_path = details['file_path']

        f = repo.get_contents(details['file_path'])

        file_content = f.decoded_content.decode('UTF-8')

        return {
            'project_id': 'N/A',
            'url': url,
            'ref': ref,
            'file_path': file_path,
            'file_content': file_content
        }



if __name__ == "__main__":
    dotenv.load_dotenv()
    file_retriever = GitHubFileRetriever(
        source_control_url=os.getenv('source_control_url'),
        source_control_pat=os.getenv('source_control_pat')
    )

    file_data = file_retriever.retrieve_file_data(
        url=""
    )


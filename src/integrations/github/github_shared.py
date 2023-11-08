import re
from github import Github, Auth


def retrieve_github_client(source_control_url: str, source_control_pat: str) -> Github:
    auth = Auth.Token(source_control_pat)
    gh = Github(auth=auth)

    return gh

def parse_pull_request_url(client: Github, url: str) -> dict:
    url_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)/pull/(?P<pull_request_id>[0-9]+)"
    match_obj = re.match(pattern=url_re, string=url)

    if match_obj is None:
        raise Exception(f"Failed to URL match against {url}")

    details = match_obj.groupdict()
    for field in ("domain", "repo_path", "pull_request_id"):
        if field not in details:
            raise Exception(f"Unable to match {field} in {url}")

    domain = details["domain"]
    repo_path = details["repo_path"]

    try:
        project = client.projects.get(repo_path)
    except Exception as ex:
        raise Exception(f"Failed to retrieve project {repo_path} from server")

    pull_request_id = details["pull_request_id"]

    return {
        "domain": domain,
        "project_id": project.get_id(),
        "repo_path": repo_path,
        "url": url,
        "pull_request_id": pull_request_id
    }
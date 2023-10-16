
import re

import gitlab

REVIEWER = 'Jarvis AI'

def retrieve_gitlab_client(
    source_control_url: str,
    source_control_pat: str,
    verify_auth: bool = True
) -> gitlab.Gitlab:
    gl = gitlab.Gitlab(
        url=source_control_url,
        private_token=source_control_pat
    )

    if verify_auth:
        gl.auth()

    return gl


def parse_url(client: gitlab.Gitlab, url: str) -> dict:
    url_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)/-/blob/(?P<ref>[a-zA-Z0-9\.\-\_]+)/(?P<file_path>.*)"
    match_obj = re.match(pattern=url_re, string=url)

    if match_obj is None:
        raise Exception(f"Failed to URL match against {url}")

    details = match_obj.groupdict()
    for field in ("domain", "repo_path", "ref", "file_path"):
        if field not in details:
            raise Exception(f"Unable to match {field} in {url}")

    domain = details["domain"]
    repo_path = details["repo_path"]

    try:
        project = client.projects.get(repo_path)
    except Exception as ex:
        raise Exception(f"Failed to retrieve project {repo_path} from server")

    ref = details["ref"]
    file_path = details["file_path"]

    return {
        "domain": domain,
        "project_id": project.get_id(),
        "repo_path": repo_path,
        "url": url,
        "ref": ref,
        "file_path": file_path
    }

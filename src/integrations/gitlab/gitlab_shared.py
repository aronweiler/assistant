import re

import gitlab

REVIEWER = "Jarvis AI"


def retrieve_gitlab_client(
    source_control_url: str, source_control_pat: str, verify_auth: bool = True
) -> gitlab.Gitlab:
    gl = gitlab.Gitlab(url=source_control_url, private_token=source_control_pat)

    if verify_auth:
        gl.auth()

    return gl


def parse_url(client: gitlab.Gitlab, url: str) -> dict:
    """Parse a URL- either a file or a diff- and return the relevant information."""

    # Sometimes the AI will generate a URL that is missing the domain. If this is the case, prepend the domain.
    url = client.url + "/" + url if not url.startswith(client.url) else url

    merge_request_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)/-/merge_requests/(?P<merge_request_iid>[0-9]+)"
    merge_request_match = re.match(pattern=merge_request_re, string=url)

    file_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)/-/blob/(?P<ref>[a-zA-Z0-9\.\-\_]+)/(?P<file_path>.*)"
    file_match = re.match(pattern=file_re, string=url)

    repo_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)"
    repo_match = re.match(pattern=repo_re, string=url)

    if merge_request_match is not None:
        mr_url_info = _parse_merge_request_url(client=client, url=url)
        mr_url_info["type"] = "diff"
        return mr_url_info
    elif file_match is not None:
        file_url_info = _parse_file_url(client=client, url=url)
        file_url_info["type"] = "file"
        return file_url_info
    elif repo_match is not None:
        repo_url_info = _parse_repo_url(client=client, url=url)
        repo_url_info["type"] = "repo"
        return repo_url_info

    raise Exception(f"Failed to URL match against {url}")


def _parse_file_url(client: gitlab.Gitlab, url: str) -> dict:
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
        "file_path": file_path,
    }


def _parse_repo_url(client: gitlab.Gitlab, url: str) -> dict:
    url_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)"
    match_obj = re.match(pattern=url_re, string=url)

    if match_obj is None:
        raise Exception(f"Failed to URL match against {url}")

    details = match_obj.groupdict()
    for field in ("domain", "repo_path"):
        if field not in details:
            raise Exception(f"Unable to match {field} in {url}")

    domain = details["domain"]
    repo_path = details["repo_path"]

    try:
        project = client.projects.get(repo_path)
    except Exception as ex:
        raise Exception(f"Failed to retrieve project {repo_path} from server")

    return {
        "domain": domain,
        "project_id": project.get_id(),
        "repo_path": repo_path,
        "url": url,
    }


def _parse_merge_request_url(client: gitlab.Gitlab, url: str) -> dict:
    url_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)/-/merge_requests/(?P<merge_request_iid>[0-9]+)"
    match_obj = re.match(pattern=url_re, string=url)

    if match_obj is None:
        raise Exception(f"Failed to URL match against {url}")

    details = match_obj.groupdict()
    for field in ("domain", "repo_path", "merge_request_iid"):
        if field not in details:
            raise Exception(f"Unable to match {field} in {url}")

    domain = details["domain"]
    repo_path = details["repo_path"]

    try:
        project = client.projects.get(repo_path)
    except Exception as ex:
        raise Exception(f"Failed to retrieve project {repo_path} from server")

    merge_request_iid = details["merge_request_iid"]

    return {
        "domain": domain,
        "project_id": project.get_id(),
        "repo_path": repo_path,
        "url": url,
        "merge_request_iid": merge_request_iid,
    }

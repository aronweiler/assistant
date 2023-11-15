import re
from github import Github, Auth


def retrieve_github_client(source_control_url: str, source_control_pat: str) -> Github:
    auth = Auth.Token(source_control_pat)
    gh = Github(auth=auth)

    return gh


def parse_url(client: Github, url: str) -> dict:
    """Parse a URL- either a file or a diff- and return the relevant information."""

    pull_request_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)/pull/(?P<pull_request_id>[0-9]+)"
    pull_request_match = re.match(pattern=pull_request_re, string=url)

    file_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)/+blob/(?P<ref>[a-zA-Z0-9\.\-\_]+)/(?P<file_path>.*)"
    file_match = re.match(pattern=file_re, string=url)

    if pull_request_match is not None:
        mr_url_info = parse_pull_request_url(
            client=client, pull_request_match=pull_request_match
        )
        mr_url_info["type"] = "diff"
        return mr_url_info
    elif file_match is not None:
        file_url_info = parse_file_url(client=client, file_match=file_match)
        file_url_info["type"] = "file"
        return file_url_info

    raise Exception(f"Failed to URL match against {url}")


def parse_file_url(client: Github, file_match, url) -> dict:
    details = file_match.groupdict()
    for field in ("domain", "repo_path", "ref", "file_path"):
        if field not in details:
            raise Exception(f"Unable to match {field} in {url}")

    domain = details["domain"]

    ref = details["ref"]
    file_path = details["file_path"]

    return {
        "type": "file",
        "domain": domain,
        "url": url,
        "ref": ref,
        "file_path": file_path,
    }


def parse_pull_request_url(client: Github, pull_request_match, url: str) -> dict:
    details = pull_request_match.groupdict()
    for field in ("domain", "repo_path", "pull_request_id"):
        if field not in details:
            raise Exception(f"Unable to match {field} in {url}")

    domain = details["domain"]
    repo_path = details["repo_path"]

    pull_request_id = details["pull_request_id"]

    return {
        "domain": domain,
        "repo_path": repo_path,
        "url": url,
        "pull_request_id": pull_request_id,
    }

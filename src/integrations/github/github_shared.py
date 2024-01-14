import re
from github import Github, Auth

REVIEWER = "Jarvis AI"


def retrieve_github_client(source_control_url:str, source_control_pat: str, requires_authentication=False) -> Github:
    if not requires_authentication:
        gh = Github(base_url=source_control_url)
        return gh
    else:
        auth = Auth.Token(source_control_pat)
        gh = Github(auth=auth, base_url=source_control_url)
        return gh


def parse_url(url: str, client:Github) -> dict:
    """Parse a URL- either a file or a diff- and return the relevant information."""

    pull_request_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)/pull/(?P<pull_request_id>[0-9]+)"
    pull_request_match = re.match(pattern=pull_request_re, string=url)

    file_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)/blob/(?P<ref>[^/]+(?:/[^/]+)*?)/(?P<file_path>.*)"
    file_match = re.match(pattern=file_re, string=url)
    
    repo_re = r"^http[s+]:\/\/(?P<domain>[a-zA-Z0-9\.\-\_]+)/(?P<repo_path>.*)"
    repo_match = re.match(pattern=repo_re, string=url)

    if pull_request_match is not None:
        mr_url_info = _parse_pull_request_url(
            pull_request_match=pull_request_match, url=url
        )
        mr_url_info["type"] = "diff"
        return mr_url_info
    elif file_match is not None:
        file_url_info = _parse_file_url(file_match=file_match, url=url, client=client)
        file_url_info["type"] = "file"
        return file_url_info
    elif repo_match is not None:
        repo_url_info = _parse_repo_url(repo_match=repo_match, url=url)
        repo_url_info["type"] = "repo"
        return repo_url_info

    raise Exception(f"Failed to URL match against {url}")


def _parse_repo_url(repo_match, url) -> dict:
    details = repo_match.groupdict()
    for field in ("domain", "repo_path"):
        if field not in details:
            raise Exception(f"Unable to match {field} in {url}")

    domain = details["domain"]
    repo_path = details["repo_path"]

    return {
        "type": "file",
        "domain": domain,
        "url": url,
        "repo_path": repo_path,
    }

def _parse_pull_request_url(pull_request_match, url: str) -> dict:
    details = pull_request_match.groupdict()
    for field in ("domain", "repo_path", "pull_request_id"):
        if field not in details:
            raise Exception(f"Unable to match {field} in {url}")

    domain = details["domain"]
    repo_path = details["repo_path"]

    pull_request_id = details["pull_request_id"]

    return {
        "type": "diff",
        "domain": domain,
        "repo_path": repo_path,
        "url": url,
        "pull_request_id": pull_request_id,
    }


def _get_github_branches(owner, repo, client:Github):
    
    repository = client.get_repo(f"{owner}/{repo}")
    branches = repository.get_branches()
    return [branch.name for branch in branches]

def _parse_file_url(file_match, url:str, client:Github):
    details = file_match.groupdict()
    domain = details['domain']
    
    # Strip the domain and everything to the left of it
    domain_index = url.index(domain)
    url = url[(domain_index + len(domain)):]
    
    # Remove protocol and split URL
    parts = url.strip('/').split('/')

    # Extract owner and repo
    owner, repo = parts[0], parts[1]

    # Get list of branches from GitHub API using PyGithub
    branches = _get_github_branches(owner, repo, client)

    # Initialize ref and file_path variables
    ref = None
    file_path = None

    # Iterate over parts to find where the ref ends
    for i in range(4, len(parts)):
        possible_ref = '/'.join(parts[3:i])
        if possible_ref in branches:
            ref = possible_ref
            file_path = '/'.join(parts[i:])
            break

    if not ref or not file_path:
        print("Could not determine ref or file_path")
        return None

    return {
        "type": "file",
        'domain': domain,
        'url': url,
        'ref': ref,
        'file_path': file_path,
        'repo_path': f"{owner}/{repo}"
    }

from github import Github, Auth


def retrieve_github_client(source_control_url: str, source_control_pat: str) -> Github:
    auth = Auth.Token(source_control_pat)
    gh = Github(auth=auth)

    return gh

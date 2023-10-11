
import gitlab


def retrieve_gitlab_client(
    gitlab_url: str,
    gitlab_pat: str,
    verify_auth: bool = True
) -> gitlab.Gitlab:
    gl = gitlab.Gitlab(
        url=gitlab_url,
        private_token=gitlab_pat
    )

    if verify_auth:
        gl.auth()

    return gl

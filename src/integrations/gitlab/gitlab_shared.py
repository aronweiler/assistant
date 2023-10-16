
import gitlab


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

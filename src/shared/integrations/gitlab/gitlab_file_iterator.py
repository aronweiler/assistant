import os
import sys
import gitlab

from src.shared.integrations.shared import TEXT_BASED_EXTENSIONS, is_text_based_extension

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.shared.integrations.gitlab import gitlab_shared


class GitlabFileIterator:
    def __init__(
        self, source_control_url, source_control_pat, requires_authentication=False
    ):
        self._gl = gitlab_shared.retrieve_gitlab_client(
            source_control_url=source_control_url,
            source_control_pat=source_control_pat,
            requires_authentication=requires_authentication,
        )

    def get_text_based_files_from_project(self, project_id, branch_name):
        project = self._gl.projects.get(project_id)
        items = project.repository_tree(ref=branch_name, recursive=True)

        matching_files = [
            item
            for item in items
            if item["type"] == "blob" and is_text_based_extension(item["path"])
        ]

        return matching_files


if __name__ == "__main__":
    # Example usage
    project_id = "your_project_id_here"

    # Get the SOURCE_CONTROL_PAT from the environment
    source_control_pat = os.environ["SOURCE_CONTROL_PAT"]

    # Retrieve the GitLab client using your source control PAT
    file_iterator = GitlabFileIterator(
        source_control_url=os.environ["SOURCE_CONTROL_URL"],
        source_control_pat=source_control_pat,
    )

    matching_files = file_iterator.get_text_based_files_from_project(
        project_id=project_id,
        branch_name="main",
    )

    for file in matching_files:
        print(file["path"])

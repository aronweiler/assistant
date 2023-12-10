import logging
from typing import List
import gitlab
import src.integrations.gitlab.gitlab_shared as gitlab_shared

from src.integrations.gitlab.gitlab_retriever import GitlabRetriever


class GitlabCommitter:
    def __init__(self, source_control_url: str, source_control_pat: str):
        self.source_control_url = source_control_url
        self.source_control_pat = source_control_pat

        self.gitlab = gitlab_shared.retrieve_gitlab_client(
            source_control_url, source_control_pat, verify_auth=True
        )

    def commit_changes(
        self,
        source_branch,
        target_branch,
        repository,
        commit_message,
        code_and_file_paths: List[dict],
    ):
        retriever = GitlabRetriever(
            source_control_url=self.source_control_url,
            source_control_pat=self.source_control_pat,
        )
        repo_data = retriever.retrieve_data(url=repository)

        project = repo_data["project"]

        # Get the latest commit of the target_branch
        try:
            target_branch_commit = project.branches.get(target_branch).commit

            # If target_branch exists, start from target_branch
            source_branch = target_branch

        except gitlab.exceptions.GitlabGetError:
            # If target_branch does not exist, start from source_branch
            source_branch_commit = project.branches.get(source_branch).commit
            target_branch_commit = source_branch_commit

        actions = [
            {
                "action": "update",
                "file_path": code_and_file_path["file_path"],
                "content": code_and_file_path["code"],
            }
            for code_and_file_path in code_and_file_paths
        ]

        # Create a new commit in the repository
        commit = project.commits.create(
            {
                "branch": target_branch,
                "commit_message": commit_message,
                "actions": actions,
                "start_branch": source_branch,
            }
        )

        logging.info("Changes committed and pushed successfully!")

    def _create_branch(self, project, source_branch, target_branch):
        try:
            branch = project.branches.get(target_branch)
            logging.info(f"Branch '{target_branch}' already exists!")
            return branch
        except gitlab.exceptions.GitlabGetError:
            pass

        branch = project.branches.create(
            {"branch": target_branch, "ref": source_branch}
        )
        logging.info(f"New branch '{target_branch}' created successfully!")
        return branch

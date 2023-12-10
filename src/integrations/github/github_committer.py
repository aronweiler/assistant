import os
import logging
from typing import List
from github import InputGitTreeElement
import src.integrations.github.github_shared as github_shared

REGULAR_FILE = "100644"


class GitHubCommitter:
    def __init__(self, source_control_pat):
        self.github = github_shared.retrieve_github_client(source_control_pat)

    def commit_changes(
        self,
        source_branch,
        target_branch,
        repository,
        commit_message,
        code_and_file_paths: List[dict],
    ):
        """Commit changes to a GitHub repository.
        
        Args:
            source_branch (str): The branch to use as the base for the new branch.
            target_branch (str): The branch to commit changes to.
            repository (str): The repository to commit changes to.
            commit_message (str): The commit message.
            code_and_file_paths (List[dict]): A list of dictionaries, each containing the following keys:
                - file_path (str): The path to the file to commit.
                - code (str): The code to commit.
        """
        repo = self.github.get_repo(repository)

        commit_branch = self._create_branch(repo, source_branch, target_branch)

        base_tree = repo.get_git_tree(sha=source_branch)

        tree_elements = []
        for code_and_file_path in code_and_file_paths:
            path = code_and_file_path["file_path"]
            code = code_and_file_path["code"]
            blob = repo.create_git_blob(content=code, encoding="utf-8")
            git_tree_element = InputGitTreeElement(
                path=path, mode=REGULAR_FILE, type="blob", sha=blob.sha
            )
            tree_elements.append(git_tree_element)

        new_tree = repo.create_git_tree(tree_elements, base_tree)

        new_commit = repo.create_git_commit(
            message=commit_message,
            tree=repo.get_git_tree(sha=new_tree.sha),
            parents=[repo.get_git_commit(repo.get_branch(source_branch).commit.sha)],
        )

        logging.info(f"{target_branch}_ref: {commit_branch}")

        commit_branch.edit(sha=new_commit.sha, force=True)

        logging.info("Changes committed and pushed successfully!")

    def _create_branch(self, repo, source_branch, target_branch):
        source_ref = repo.get_git_ref(f"heads/{source_branch}")
        commit_sha = source_ref.object.sha

        try:
            branch = repo.get_git_ref(f"heads/{target_branch}")
            logging.info(f"Branch '{target_branch}' already exists!")
            return branch
        except:
            pass

        new_branch = repo.create_git_ref(f"refs/heads/{target_branch}", commit_sha)
        logging.info(f"New branch '{target_branch}' created successfully!")
        return new_branch

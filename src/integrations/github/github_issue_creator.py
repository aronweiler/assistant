import json
import logging
import os
import pathlib
import sys

import dotenv
from github import Github
import jinja2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Assuming you have a similar shared module for GitHub as you did for GitLab.
import src.integrations.github.github_shared as github_shared


logging.basicConfig(level=os.getenv("LOGGING_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def load_review_from_json_file(file_loc: pathlib.Path | str) -> dict:
    with open(file_loc, "r") as f:
        data = json.load(f)
    return data


class GitHubIssueCreator:
    def __init__(self, source_control_url, source_control_pat):
        self._gh = github_shared.retrieve_github_client(
            source_control_url=source_control_url, source_control_pat=source_control_pat
        )

    @staticmethod
    def _get_template():
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                [pathlib.Path(__file__).parent.resolve() / "templates"]
            ),
            autoescape=jinja2.select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = env.get_template("code_review_issue_template.md.j2")
        return template

    @staticmethod
    def _preprocess_review(review_data: dict) -> dict:
        TAB_WIDTH = 4
        for comment in review_data["comments"]:
            for key in ("original_code_snippet", "suggested_code_snippet"):
                if key in comment:
                    if comment[key] == "":
                        del comment[key]
                    else:
                        comment[key] = comment[key].expandtabs(TAB_WIDTH)
        return review_data

    def generate_issue(
        self,
        review_data: dict,
        metadata: dict,
    ):
        repo_name = metadata["repo_name"]
        ref = metadata["ref"]
        source_code_file_loc = metadata["source_code_file_loc"]
        source_code_file_href = metadata["source_code_file_href"]

        repo = self._gh.get_repo(repo_name)

        title = (
            f"{github_shared.REVIEWER} review of {source_code_file_loc} (ref: {ref})"
        )

        review_data = self._preprocess_review(review_data=review_data)

        language = review_data.get("language", "")
        description_template = self._get_template()
        description = description_template.render(
            source_code_file_path=source_code_file_loc,
            source_code_href=source_code_file_href,
            reviewer=github_shared.REVIEWER,
            comments=review_data["comments"],
            language_mode_syntax_highlighting=language,
        )

        issue = repo.create_issue(
            title=title, body=description, labels=[github_shared.REVIEWER]
        )

        return {"url": issue.html_url}


if __name__ == "__main__":
    dotenv.load_dotenv()
    issue_creator = GitHubIssueCreator(
        source_control_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
        source_control_pat=os.getenv("SOURCE_CONTROL_PAT"),
    )

    review_data = load_review_from_json_file(
        file_loc=pathlib.Path(__file__).parent.resolve()
        / "test"
        / "data"
        / "comment_data_3.json"
    )

    issue_creator.generate_issue(
        repo_name="aronweiler/assistant",
        ref="main",
        source_code_file_loc="About.py",
        source_code_file_href="https://github.com/aronweiler/assistant/blob/main/About.py",
        review_data=review_data,
    )

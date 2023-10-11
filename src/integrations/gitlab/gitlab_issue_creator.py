
import json
import logging
import os
import pathlib
import sys

import dotenv
import gitlab
import jinja2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import src.integrations.gitlab.gitlab_shared as gitlab_shared


logging.basicConfig(level=os.getenv("LOGGING_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def load_review_from_json_file(file_loc: pathlib.Path | str) -> dict:
    with open(file_loc, 'r') as f:
        data = json.load(f)

    return data


class GitlabIssueCreator:

    def __init__(self, gitlab_url, gitlab_pat):
        self._gl = gitlab_shared.retrieve_gitlab_client(
            gitlab_url=gitlab_url,
            gitlab_pat=gitlab_pat,
            verify_auth=True
        )      
    

    @staticmethod
    def _get_template():
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                [pathlib.Path(__file__).parent.resolve() / 'templates']
            ),
            autoescape=jinja2.select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True
        )

        template = env.get_template("code_review_issue_template.md.j2")
        return template


    @staticmethod
    def _preprocess_review(review_data: dict) -> dict:

        # Replace all tabs with TAB_WIDTH
        # Remove any code snippets which are empty strings
        TAB_WIDTH = 4
        for comment in review_data['comments']:
            for key in ('original_code_snippet', 'suggested_code_snippet'):
                if key in comment:
                    if comment[key] == "":
                        del comment[key]
                    else:
                        comment[key] = comment[key].expandtabs(TAB_WIDTH)
                   
        return review_data


    def generate_issue(
            self,
            project_id: int,
            ref: str,
            source_code_file_loc: str | pathlib.Path,
            source_code_file_href: str,
            review_data: dict):
        
        REVIEWER = 'Jarvis AI'

        project = self._gl.projects.get(id=project_id)
        # issues = project.issues.list()
        
        title = f"Review of file {source_code_file_loc}"

        review_data = self._preprocess_review(review_data=review_data)
        language = review_data.get('language',"")
        description_template = self._get_template()
        description = description_template.render(
            source_code_file_path=source_code_file_loc,
            source_code_href=source_code_file_href,
            reviewer=REVIEWER,
            comments=review_data['comments'],
            language_mode_syntax_highlighting=language
        )

        # Debug output to file
        # with open(pathlib.Path(__file__).parent.resolve() / "test" / "data" / "rendered_issue.md", "w") as fh:
        #     fh.write(description)

        issue = project.issues.create(
            {
                'title': title,
                'description': description,
                'labels': [
                    REVIEWER
                ]
            }
        )

        issue.save()

        return {
            'url': issue.web_url
        }


if __name__ == "__main__":
    dotenv.load_dotenv()
    issue_creator = GitlabIssueCreator(
        gitlab_url=os.getenv('GITLAB_URL'),
        gitlab_pat=os.getenv('GITLAB_PAT')
    )

    review_data = load_review_from_json_file(
        file_loc=pathlib.Path(__file__).parent.resolve() / "test" / "data" / "comment_data_2.json"
    )

    issue_creator.generate_issue(
        project_id=13881,
        ref='main',
        source_code_file_loc='samples/StateMachine/Motor.cpp',
        source_code_file_href='https://code.medtronic.com/Ventilation/sandbox/llm-integration-prototypes/-/blob/main/samples/StateMachine/Motor.cpp',
        review_data=review_data
    )

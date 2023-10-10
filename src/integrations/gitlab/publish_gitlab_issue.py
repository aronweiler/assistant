
import json
import logging
import os
import pathlib

import dotenv
import gitlab
import jinja2


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def load_review(file_loc: pathlib.Path | str) -> dict:
    with open(file_loc, 'r') as f:
        data = json.load(f)

    return data


def get_template():
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


def main():

    review_file_loc = pathlib.Path(__file__).parent.resolve() / "test" / "data" / "comment_data_2.json"
    review = load_review(file_loc=review_file_loc)
    gl = gitlab.Gitlab(
        url='https://code.medtronic.com',
        private_token=os.getenv('GITLAB_PAT')
    )

    # gl.enable_debug()
    gl.auth()
    
    # logger.info("Projects in group:")
    # VENTILATION_GROUP_ID = 5850
    CODE_SPLITTER_PROJECT_ID = 14163

    project = gl.projects.get(id=CODE_SPLITTER_PROJECT_ID)
    # print(project)
    issues = project.issues.list()
    
    source_code_file = 'cpp_splitter.py'
    source_code_href = 'https://code.medtronic.com/Ventilation/sandbox/code-splitter/-/blob/8d90e484d4d41601e5b610b20bc271ee4fb2e19b/codesplitter/splitter/cpp_splitter/cpp_splitter.py'
    title = f"Review of file {source_code_file}"

    description_template = get_template()
    description = description_template.render(
        source_code_file_path=source_code_file,
        source_code_href=source_code_href,
        reviewer="Jarvis AI",
        comments=review['comments']
    )

    # Debug output to file
    # with open(pathlib.Path(__file__).parent.resolve() / "test" / "data" / "rendered_issue.md", "w") as fh:
    #     fh.write(description)

    issue = project.issues.create(
        {
            'title': title,
            'description': description,
            'labels': [
                'Jarvis AI'
            ]
        }
    )

    issue.save()

    # group = gl.groups.get(VENTILATION_GROUP_ID)
    # for project in group.projects.list(iterator=True):
    #     print(project)

    # logger.info("All projects:")
    # projects = gl.projects.list(iterator=True)
    # for project in projects:
    #     print(project)


if __name__ == "__main__":
    dotenv.load_dotenv()
    main()

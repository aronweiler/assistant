
import json
import logging
import os
import pathlib

import dotenv
import gitlab

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def load_review(file_loc: pathlib.Path | str) -> dict:
    with open(file_loc, 'r') as f:
        data = json.load(f)

    return data


def main():

    review_file_loc = pathlib.Path(__file__).parent.resolve() / "test" / "data" / "comment_data_0.json"
    review = load_review(file_loc=review_file_loc)#'/test/data/comment_data_0.json')
    gl = gitlab.Gitlab(
        url='https://code.medtronic.com',
        private_token=os.getenv('GITLAB_PAT')
    )

    # gl.enable_debug()
    gl.auth()
    
    logger.info("Projects in group:")
    VENTILATION_GROUP_ID = 5850
    CODE_SPLITTER_PROJECT_ID = 14163

    project = gl.projects.get(id=CODE_SPLITTER_PROJECT_ID)
    # print(project)
    issues = project.issues.list()
    
    source_code_file = 'tbd.cpp'
    title = f"Review of file {source_code_file}"
    description = f"""
        The file {source_code_file} from URL tbd was reviewed with the following findings:
        {review}
    """
    issue = project.issues.create(
        {
            'title': title,
            'description': description,
            'labels': [
                'Jarvis AI'
            ]
        }
    )
    # issue.labels([
    #     'Jarvis'
    # ])

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

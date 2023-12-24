from ast import List
import os
import sys
import logging

from github.ContentFile import ContentFile


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.integrations.github import github_shared


def get_text_based_files_from_repo(source_control_pat: str, repository_name: str, branch_name: str, path: str = ""):
    # Retrieve the Github client using your source control PAT
    github_client = github_shared.retrieve_github_client(source_control_pat)

    # Get the repository
    repository = github_client.get_repo(repository_name)

    matching_files = []

    # Iterate through all files in all directories
    contents = repository.get_contents(ref=branch_name, path=path)
    while contents:
        file_content = contents.pop(0)
        
        if file_content.type == "dir":
            contents.extend(repository.get_contents(file_content.path))
        else:
            if is_text_based_file(file_content):
                logging.info(f"Found text-based file: {file_content.name}")
                matching_files.append(file_content)
            else:
                logging.info(f"Skipping non-text-based file: {file_content.name}")

    return matching_files


def is_text_based_file(file_content:ContentFile):
   
    logging.info(f"Checking if {file_content.name} is text-based.")
   
    # Check if content is base64 encoded
    if file_content.encoding == 'base64':
        try:
            # Try to decode the content
            text_content = file_content.decoded_content.decode('utf-8')

            # Check for non-text characters (heuristic)
            if '\0' in text_content:
                logging.debug("The file appears to be binary.")
                return False
            else:
                logging.debug("The file appears to be text-based.")
                return True
        except UnicodeDecodeError:
            logging.debug("Decoding error: The file might be binary.")
            return False
    else:
        logging.debug("The encoding type is not base64, so this method may not apply.")
        return False

if __name__ == "__main__":
    # Example usage
    repository_name = "aronweiler/assistant"
    
    # Get the SOURCE_CONTROL_PAT from the environment
    source_control_pat = os.environ["SOURCE_CONTROL_PAT"]

    matching_files = get_text_based_files_from_repo(repository_name=repository_name, branch_name="main", source_control_pat=source_control_pat, path="src/ui")

    for file in matching_files:
        print(file)

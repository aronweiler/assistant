import sys
import os
from typing import List

# Importing necessary modules and classes for the tool.
from langchain.base_language import BaseLanguageModel

# Adjusting system path to include the root directory for module imports.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.ai.llm_helper import get_tool_llm
from src.integrations.github import github_issue_creator
from src.tools.code.issue_tool import IssueTool


# Importing database models and utilities.
from src.db.models.documents import Documents
from src.ai.conversations.conversation_manager import ConversationManager
from src.utilities.token_helper import num_tokens_from_string
from src.utilities.parsing_utilities import parse_json

# Importing integration modules for GitLab and GitHub.
from src.integrations.gitlab.gitlab_issue_creator import GitlabIssueCreator
from src.integrations.gitlab.gitlab_issue_retriever import GitlabIssueRetriever
from src.integrations.gitlab.gitlab_retriever import GitlabRetriever

from src.integrations.github.github_issue_creator import GitHubIssueCreator
from src.integrations.github.github_retriever import GitHubRetriever


class CodeRefactorTool:
    """
    A tool for conducting code refactors using different source control providers.
    It can retrieve files from URLs or files from the database, conduct refactors on those files,
    and format the results in a structured way.
    """

    # Mapping of source control provider names to their respective retriever classes.
    source_control_to_retriever_map = {
        "gitlab": GitlabRetriever,
        "github": GitHubRetriever,
    }

    def __init__(
        self,
        configuration,
        conversation_manager: ConversationManager,
    ):
        """
        Initializes the CodeRefactorTool with a given configuration and an conversation manager.

        :param configuration: Configuration settings for the tool.
        :param conversation_manager: The manager that handles interactions with language models.
        """
        self.configuration = configuration
        self.conversation_manager = conversation_manager

        # Constants for environment variables and source control providers
        self.source_control_provider = os.getenv(
            "SOURCE_CONTROL_PROVIDER", "github"
        ).lower()
        self.source_control_url = os.getenv("source_control_url")
        self.source_control_pat = os.getenv("source_control_pat")

    def get_active_code_refactor_templates(self, tool_name: str) -> List[dict]:
        """
        Retrieves active code refactor templates based on the provided tool name.

        :param tool_name: Name of the tool for which to retrieve templates.
        :return: A list of dictionaries containing template names and descriptions.
        """

        # Access additional settings specific to the tool from configuration.
        additional_settings = self.configuration["tool_configurations"][tool_name][
            "additional_settings"
        ]

        templates = []
        template_checks = {
            "security_code_refactor": "Security",
            "performance_code_refactor": "Performance",
            "memory_code_refactor": "Memory",
            "correctness_code_refactor": "Correctness",
            "maintainability_code_refactor": "Maintainability",
            "reliability_code_refactor": "Reliability",
        }

        for setting, description in template_checks.items():
            if additional_settings[f"enable_{setting}"]["value"]:
                templates.append(
                    {"name": f"{setting.upper()}_TEMPLATE", "description": description}
                )

        return templates

    def retrieve_source_code_from_url(self, url: str) -> str:
        """
        Retrieves source code from a given URL using the appropriate source control provider.

        :param url: The URL from which to retrieve the source code file.
        :return: The retrieved source code or an error message if retrieval is not supported.
        """
        # Get the corresponding retriever class from the map using provider name in lowercase.
        retriever_class = self.source_control_to_retriever_map.get(
            self.source_control_provider
        )

        # If no retriever class is found, return an error message indicating unsupported file retrieval.
        if not retriever_class:
            return f"Source control provider {self.source_control_provider} does not support file retrieval"

        # Instantiate the retriever with necessary credentials from environment variables.
        retriever_instance = retriever_class(
            self.source_control_url,
            self.source_control_pat,
        )

        # Use the instantiated retriever to fetch data from the provided URL.
        return retriever_instance.retrieve_data(url=url)

    def _conduct_code_refactor(
        self,
        file_data: str,
        llm: BaseLanguageModel,
        tool_name: str,
        additional_instructions: str = None,
        metadata: dict = None,
    ) -> dict:
        """
        Conducts a refactor on a file.

        :param file_data: The raw content of the file to be refactored.
        :param llm: An instance of a language model used for generating predictions during refactors.
        :param tool_name: Name of the tool initiating this code refactor process.
        :param additional_instructions: Additional instructions provided by users for this specific refactor task (optional).
        :param metadata: Metadata associated with this file (optional).
        :return: A dictionary containing results of the code refactor process.
        """

        # Note: Not doing this in refactors
        # Split the file data into lines and prepend line numbers for clarity.
        # code_with_line_numbers = [
        #     f"{line_num + 1}: {line}"
        #     for line_num, line in enumerate(file_data.splitlines())
        # ]

        # Retrieve base code refactor instructions and format them with file-specific instructions.
        base_code_refactor_instructions = (
            self.conversation_manager.prompt_manager.get_prompt(
                "code_refactor", "BASE_CODE_REFACTOR_INSTRUCTIONS_TEMPLATE"
            )
        )

        code_refactor_format_instructions = (
            self.conversation_manager.prompt_manager.get_prompt(
                "code_refactor", "CODE_REFACTOR_FORMAT_TEMPLATE"
            )
        )

        # Format the base instructions to include the file-specific format instructions.
        base_code_refactor_instructions = base_code_refactor_instructions.format(
            format_instructions=code_refactor_format_instructions
        )

        # Run the code refactors using the formatted instructions and return the results.
        return self._run_code_refactors(
            code=file_data,
            base_code_refactor_instructions=base_code_refactor_instructions,
            llm=llm,
            tool_name=tool_name,
            additional_instructions=additional_instructions,
            metadata=metadata,
        )

    def _run_code_refactors(
        self,
        code: List[str],
        base_code_refactor_instructions: str,
        llm: BaseLanguageModel,
        tool_name: str,
        additional_instructions: str = None,
        metadata: dict = None,
    ) -> dict:
        """
        Runs code refactors using provided instructions and a language model.

        :param code: A list of strings representing the code to be refactored.
        :param base_code_refactor_instructions: The base instructions for conducting the refactor.
        :param llm: An instance of a language model used for generating predictions during refactors.
        :param tool_name: Name of the tool initiating this code refactor process.
        :param additional_instructions: Additional instructions provided by users for this specific refactor task (optional).
        :param metadata: Metadata associated with this refactor (optional).
        :return: A dictionary containing results of the code refactor process.
        """

        # Retrieve active templates based on the tool name.
        templates = self.get_active_code_refactor_templates(tool_name)

        # Initialize containers for results
        refactor_results = []

        if len(templates) == 0:
            # If the templates are all turned off, just use the additional instructions
            # If there are no additional instructions, don't perform a refactor, throw an exception
            if not additional_instructions or additional_instructions == "":
                raise Exception(
                    "No refactor templates are enabled and no additional instructions were provided"
                )

            data = self._process_additional_instructions(
                base_code_refactor_instructions=base_code_refactor_instructions,
                additional_instructions=additional_instructions,
                metadata=metadata,
                code=code,
                llm=llm,
            )
            
            code = data["refactored_code"]

            refactor_results.append(data)

        else:
            # Format additional instructions if provided.
            if additional_instructions:
                additional_instructions = f"\nIn addition to the base code refactor instructions, consider these user-provided instructions:\n{additional_instructions}\n"

            code = self._process_templates(
                templates=templates,
                refactor_results=refactor_results,
                metadata=metadata,
                additional_instructions=additional_instructions,
                base_code_refactor_instructions=base_code_refactor_instructions,
                code=code,
                llm=llm,
            )

        # Extract metadata from the last set of data processed (assumes consistent structure across all templates).
        refactor_metadata = refactor_results[0]["metadata"]

        # Compile final refactor results including language, metadata, and comments.
        results = {
            "language": refactor_results[0]["language"],
            "metadata": refactor_metadata,
            "refactor_thoughts": [
                {
                    "refactor_type": refactor["refactor_type"],
                    "thoughts": refactor["thoughts"],
                }
                for refactor in refactor_results
            ],
            "refactored_code": code,
        }

        if self.is_output_json(tool_name):
            # Return formatted refactor results as a JSON string enclosed in triple backticks for markdown formatting.
            return f"```json\n{results}\n```"
        else:
            return self.format_refactor_results(results)

    def _process_additional_instructions(
        self,
        base_code_refactor_instructions,
        additional_instructions,
        metadata,
        code,
        llm,
    ):
        final_code_refactor_instructions = (
            self.conversation_manager.prompt_manager.get_prompt(
                "code_refactor", "FINAL_CODE_REFACTOR_INSTRUCTIONS"
            ).format(
                code_summary="",
                code_dependencies="",
                code=code,
                code_metadata=metadata,
                additional_instructions="",
            )
        )

        # Get individual prompt for each type of refactor from the template and format it.
        code_refactor_prompt = self.conversation_manager.prompt_manager.get_prompt(
            "code_refactor", "CUSTOM_CODE_REFACTOR_TEMPLATE"
        ).format(
            base_code_refactor_instructions=base_code_refactor_instructions,
            final_code_refactor_instructions=final_code_refactor_instructions,
            code_refactor_instructions=additional_instructions,
        )

        # Use language model to predict based on the formatted prompt.
        json_data = llm.predict(
            code_refactor_prompt,
            callbacks=self.conversation_manager.agent_callbacks,
        )

        # Parse JSON data returned by language model prediction into structured data.
        data = parse_json(json_data, llm)

        
        
        if "final_answer" in data:
            # The AI fucked up, and can't actually do its job... surprise surprise
            return data["final_answer"]

        # Set the old code to the new code
        code = data["refactored_code"]
        data["refactor_type"] = f" Custom instructions\n{additional_instructions}"

        return data

    def _process_templates(
        self,
        refactor_results,
        templates,
        metadata,
        additional_instructions,
        base_code_refactor_instructions,
        code,
        llm,
    ):
        # Iterate over each template and perform a refactor using the language model.
        for template in templates:
            # Format final code refactor instructions with placeholders replaced by actual data.
            # Note: This needs to be in the loop, because we're going to keep feeding the output of the previous refactor
            # into the next refactor.
            final_code_refactor_instructions = (
                self.conversation_manager.prompt_manager.get_prompt(
                    "code_refactor", "FINAL_CODE_REFACTOR_INSTRUCTIONS"
                ).format(
                    code_summary="",
                    code_dependencies="",
                    code=code,
                    code_metadata=metadata,
                    additional_instructions=additional_instructions,
                )
            )

            # Get individual prompt for each type of refactor from the template and format it.
            code_refactor_prompt = self.conversation_manager.prompt_manager.get_prompt(
                "code_refactor", template["name"]
            ).format(
                base_code_refactor_instructions=base_code_refactor_instructions,
                final_code_refactor_instructions=final_code_refactor_instructions,
            )

            # Use language model to predict based on the formatted prompt.
            json_data = llm.predict(
                code_refactor_prompt,
                callbacks=self.conversation_manager.agent_callbacks,
            )

            # Parse JSON data returned by language model prediction into structured data.
            data = parse_json(json_data, llm)

            if "final_answer" in data:
                # The AI fucked up, and can't actually do its job... surprise surprise
                return data["final_answer"]

            # Feed the results of the refactor into the next refactor.
            code = data["refactored_code"]

            data["refactor_type"] = template["description"]

            # Append results from current template's refactor.
            # Note: This is not currently used anywhere- the ultimate result of this tool is just the final code
            # However, this is here so that we can do something with the data generated by each of the steps in the future.
            refactor_results.append(data)
            
        return code

    def conduct_code_refactor_from_url(
        self, target_url: str, additional_instructions: str = None
    ) -> str:
        """
        Conducts a code refactor on a file or diff obtained from a given URL.

        :param target_url: The URL of the source code to be refactored.
        :param additional_instructions: Additional instructions provided by users for this specific refactor task (optional).
        :return: A string containing the formatted results of the code refactor in JSON.
        """

        # Retrieve file information from the URL.
        file_info = self.retrieve_source_code_from_url(url=target_url)

        # Determine the type of file and conduct appropriate type of refactor.
        return self._refactor_file_from_url(
            file_info, target_url, additional_instructions
        )

    def _refactor_file_from_url(
        self, file_info: dict, target_url: str, additional_instructions: str
    ) -> dict:
        """
        Conducts a code refactor on a single file from a URL and returns structured results.

        :param file_info: Metadata and content information about the file.
        :param target_url: The URL of the source code to be refactored.
        :param additional_instructions: Additional instructions provided by users for this specific refactor task (optional).
        :return: A dictionary containing the results of the file code refactor.
        """

        # Extract file content from file_info and remove 'file_content' key.
        file_data = file_info.pop("file_content", None)

        # Calculate the number of tokens in the code file for size check.
        code_file_token_count = num_tokens_from_string(file_data)

        # Get maximum allowed token count for a code refactor based on tool configuration.
        max_token_count = self.get_max_code_refactor_token_count(
            self.conduct_code_refactor_from_url.__name__
        )

        # If the file is too large, return an error message indicating so.
        if code_file_token_count > max_token_count:
            return f"File is too large to be refactored ({code_file_token_count} tokens). Adjust max code refactor tokens, or refactor this code file so that it's smaller."

        # Initialize language model for prediction.
        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.conduct_code_refactor_from_url.__name__,
            streaming=True,
        )

        # Conduct a refactor on the entire file content and return the results.
        return self._conduct_code_refactor(
            file_data=file_data,
            additional_instructions=additional_instructions,
            metadata=file_info,
            llm=llm,
            tool_name=self.conduct_code_refactor_from_url.__name__,
        )

    def get_max_code_refactor_token_count(self, tool_name: str) -> int:
        """
        Retrieves the maximum token count allowed for a code refactor based on tool configuration.

        :param tool_name: Name of the tool for which to retrieve the maximum token count.
        :return: The maximum number of tokens allowed in a code refactor.
        """

        # Access the max_code_size_tokens setting from the tool configuration and return its value.
        return self.configuration["tool_configurations"][tool_name][
            "additional_settings"
        ]["max_code_size_tokens"]["value"]

    def is_output_json(self, tool_name: str) -> int:
        """
        Retrieves the maximum token count allowed for a code refactor based on tool configuration.

        :param tool_name: Name of the tool for which to retrieve the maximum token count.
        :return: The maximum number of tokens allowed in a code refactor.
        """

        # Access the max_code_size_tokens setting from the tool configuration and return its value.
        return self.configuration["tool_configurations"][tool_name][
            "additional_settings"
        ]["json_output"]["value"]

    def conduct_code_refactor_from_file_id(
        self, target_file_id: int, additional_instructions: str = None
    ) -> dict:
        """
        Conducts a code refactor on a file identified by its database ID.

        :param target_file_id: The database ID of the file to be refactored.
        :param additional_instructions: Additional instructions provided by users for this specific refactor task (optional).
        :return: A dictionary containing the results of the code refactor.
        """

        # Format additional instructions if provided.
        if additional_instructions:
            additional_instructions = f"\n--- ADDITIONAL INSTRUCTIONS ---\n{additional_instructions}\n--- ADDITIONAL INSTRUCTIONS ---\n"

        # Retrieve file model from database using Documents class and file ID.
        documents = Documents()
        file_model = documents.get_file(file_id=target_file_id)

        # Check if the retrieved file is classified as code; if not, return an error message.
        if file_model.file_classification.lower() != "code":
            return "File is not code. Please select a code file to conduct a refactor on, or use a different tool."

        # Get raw file data from database and decode it.
        file_data = documents.get_file_data(file_model.id).decode("utf-8")

        # Initialize language model for prediction.
        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.conduct_code_refactor_from_file_id.__name__,
            streaming=True,
        )

        # Conduct a refactor on the entire file content and return the results.
        return self._conduct_code_refactor(
            file_data=file_data,
            additional_instructions=additional_instructions,
            metadata={"filename": file_model.file_name},
            llm=llm,
            tool_name=self.conduct_code_refactor_from_file_id.__name__,
        )

    def format_refactor_results(self, refactor_results: dict) -> str:
        """
        Formats the results of a code refactor into a string.

        :param refactor_results: The results of a code refactor.
        :return: A string containing the formatted results of the code refactor.
        """
        formatted_results = """## Code Refactor
- Language: **{language}**
- File: **{filename_or_url}**

{thoughts}

### Refactored Code
```{language}
{code}
```
"""

        thoughts = "\n\n".join(
            [
                f"#### {thought['refactor_type']}\n- {thought['thoughts']}"
                for thought in refactor_results["refactor_thoughts"]
            ]
        )

        formatted_results = formatted_results.format(
            language=refactor_results["language"],
            filename_or_url=refactor_results["metadata"]["url"]
            if "url" in refactor_results["metadata"]
            else refactor_results["metadata"]["filename"],
            thoughts=thoughts,
            code=refactor_results["refactored_code"],
        )

        # Return the formatted results.
        return formatted_results


if __name__ == "__main__":

    # Create an instance of the code refactor tool.
    code_refactor_tool = CodeRefactorTool(
        configuration=None,
        conversation_manager=None,
    )

    temp = {
        "language": "python",
        "metadata": {
            "type": "file",
            "project_id": "N/A",
            "url": "https://github.com/aronweiler/CodeReviewer/blob/main/src/integrations/github_integration.py",
            "ref": "main",
            "file_path": "src/integrations/github_integration.py",
            "repo_path": "aronweiler/CodeReviewer",
        },
        "thoughts": "The refactoring focuses on improving the initialization of the GitHubIntegration class to allow for reusability and configuration. The commit_changes function has been updated to use the configuration parameters set during initialization. Error handling has been improved, and the code has been cleaned up to remove unnecessary comments and debug prints. The code now adheres more closely to best practices.",
        "refactored_code": 'import logging\nimport os\nfrom github import Github, InputGitTreeElement\n\nREGULAR_FILE = "100644"\n\n\nclass GitHubIntegration:\n    def __init__(self, github_token, repository):\n        if not github_token:\n            raise ValueError("GitHub token must be provided")\n        if not repository:\n            raise ValueError("GitHub repository must be provided")\n\n        self.github_token = github_token\n        self.repository = repository\n        self.github = Github(self.github_token)\n\n    def commit_changes(self, source_branch, target_branch, commit_message, metadatas):\n        repo = self.github.get_repo(self.repository)\n\n        # This call ensures the branch is created\n        commit_branch = self._create_branch(repo, source_branch, target_branch)\n\n        # Get the base tree\n        base_tree = repo.get_git_tree(sha=source_branch)\n\n        # Create a new tree with the changes\n        tree_elements = [\n            InputGitTreeElement(\n                path=metadata["file_path"],\n                mode=REGULAR_FILE,\n                type="blob",\n                sha=repo.create_git_blob(content=metadata["code"], encoding="utf-8").sha\n            ) for metadata in metadatas\n        ]\n\n        new_tree = repo.create_git_tree(tree_elements, base_tree)\n\n        # Create the commit\n        new_commit = repo.create_git_commit(\n            message=commit_message,\n            tree=new_tree,\n            parents=[repo.get_commit(repo.get_branch(source_branch).commit.sha)]\n        )\n\n        # Push the commit to the new branch by editing the reference\n        commit_branch.edit(sha=new_commit.sha, force=True)\n\n        logging.info("Changes committed and pushed successfully!")\n\n    def _create_branch(self, repo, source_branch, target_branch):\n        # Get the latest commit of the source branch\n        source_ref = repo.get_git_ref(f"heads/{source_branch}")\n        commit_sha = source_ref.object.sha\n\n        # See if the target branch already exists\n        try:\n            branch = repo.get_git_ref(f"heads/{target_branch}")\n            logging.info(f"Branch \'{target_branch}\' already exists!")\n            return branch\n        except:\n            # Create the new branch with the specified commit\n            new_branch = repo.create_git_ref(f"refs/heads/{target_branch}", commit_sha)\n            logging.info(f"New branch \'{target_branch}\' created successfully!")\n            return new_branch\n\n\nif __name__ == "__main__":\n    logging.basicConfig(level=logging.INFO)\n    github_integration = GitHubIntegration(\n        github_token=os.getenv("GITHUB_TOKEN"),\n        repository=os.getenv("GITHUB_REPOSITORY")\n    )\n\n    github_integration.commit_changes(\n        source_branch="main",\n        target_branch="test-branch",\n        commit_message="Test commit",\n        metadatas=[\n            {\n                "file_path": "examples/code_comment.py",\n                "code": "def test():\\n    print(\'hello world\')\\n"\n            }\n        ]\n    )',
    }

    results = {
        "language": temp["language"],
        "metadata": temp["metadata"],
        "refactor_thoughts": [{
            "refactor_type": "Custom",
            "thoughts": temp["thoughts"],
        }],
        "refactored_code": temp["refactored_code"],
    }

    bleh = code_refactor_tool.format_refactor_results(results)
    print(bleh)

import sys
import os
import logging
from typing import List

from langchain.chains.llm import LLMChain
from langchain.base_language import BaseLanguageModel
from langchain.chains import (
    RetrievalQAWithSourcesChain,
    StuffDocumentsChain,
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.db.models.conversations import SearchType
from src.db.models.documents import Documents
from src.ai.interactions.interaction_manager import InteractionManager

from src.utilities.token_helper import num_tokens_from_string

from src.db.models.pgvector_retriever import PGVectorRetriever

from src.ai.llm_helper import get_prompt

from src.tools.code.code_dependency import CodeDependency


class CodeTool:
    def __init__(
        self,
        configuration,
        interaction_manager: InteractionManager,
        llm: BaseLanguageModel,
    ):
        self.configuration = configuration
        self.interaction_manager = interaction_manager
        self.llm = llm

    def get_pretty_dependency_graph(self, target_file_id) -> str:
        """Get a graph of the dependencies for a given file.

        Args:
            target_file_id: The id of the file to get the dependencies for.
        """

        dependency_graph = self.get_dependency_graph(target_file_id)

        if len(dependency_graph.dependencies) == 0:
            return f"{dependency_graph.name} has no dependencies"

        pretty_dependencies = self.pretty_print_dependency_graph(dependency_graph)

        return pretty_dependencies

    def get_dependency_graph(self, target_file_id) -> CodeDependency:
        """Get a graph of the dependencies for a given file.

        Args:
            target_file_id: The id of the file to get the dependencies for.
        """
        documents = Documents()

        # Get the list of documents
        document_chunks = documents.get_document_chunks_by_file_id(
            target_file_id=target_file_id,
        )

        # Get the list of top-level includes
        code_dependency = CodeDependency(
            name=document_chunks[0].document_name, dependencies=[]
        )
        for doc in document_chunks:
            if doc.additional_metadata["type"] == "MODULE":
                # This might need to be something other than "includes" at some point
                for include in doc.additional_metadata["includes"]:
                    # strip the filename from the path
                    filename = include.split("/")[-1]
                    if (
                        not [
                            d
                            for d in code_dependency.dependencies
                            if d.name == filename
                        ]
                        and not filename == code_dependency.name
                    ):
                        file = documents.get_file_by_name(
                            filename, self.interaction_manager.collection_id
                        )
                        if file:
                            # Get the dependencies
                            code_dependency.dependencies.append(
                                self.get_dependency_graph(file.id)
                            )

        return code_dependency

    def pretty_print_dependency_graph(
        self, code_dependency: CodeDependency, indent: int = 0
    ):
        """
        Pretty print the dependency graph in Markdown format.

        Args:
            code_dependency: The dependency graph to print.
            indent: The indent level to use for the print.
        """
        output = " " * indent + f"- {code_dependency.name}"
        for dependency in code_dependency.dependencies:
            output += "\n" + self.pretty_print_dependency_graph(dependency, indent + 2)

        return output

    # NOTE!
    ## TODO: This can return enormous amounts of data, depending on the size of the file-
    # need to chunk the results up and then run a chain over them to answer
    def code_structure(
        self,
        target_file_id: int,
        code_type: str = None,
    ):
        """Useful for looking at the code structure of a single file. This tool only works when you specify a file. It will give you a list of module names, function signatures, and class method signatures in the specified file (represented by the 'target_file_id').
        You can use the signature provided by this tool to call 'code_details' in order to get the underlying code.

        Make sure not to use this tool on anything that isn't classified as 'Code'.

        Args:
            target_file_id (int): REQUIRED! Cannot be null. The loaded 'Code' classified file ID you would like to get the code structure for.
            code_type (str, optional): Valid code_type arguments are 'MODULE', 'FUNCTION_DECLARATION', and 'CLASS_METHOD'. When left empty, the code structure will be returned in its entirety.
        """

        if not target_file_id:
            return "target_file_id is required!  Check the loaded documents, and try again."

        documents = Documents()

        try:
            document_chunks = documents.get_document_chunks_by_file_id(target_file_id)

            # Create a list of unique metadata entries from the document chunks
            full_metadata_list = []
            modules = []
            functions = []
            class_methods = []
            others = []

            self.get_metadata(
                full_metadata_list,
                modules,
                functions,
                class_methods,
                others,
                document_chunks,
            )

            # Custom sorting key function
            def custom_sorting_key(item):
                # Assign a higher value (e.g., 0) to "MODULE" type, lower value (e.g., 1) to others
                return 0 if item["type"] == "MODULE" else 1

            if code_type is not None:
                if code_type == "MODULE":
                    code_structure = (
                        "Modules:\n\t"
                        + "\n\t".join([m["filename"] for m in modules])
                        + "\n\n"
                    )
                elif code_type == "FUNCTION_DECLARATION":
                    code_structure = (
                        "Functions:\n\t"
                        + "\n\t".join([f["signature"] for f in functions])
                        + "\n\n"
                    )
                elif code_type == "CLASS_METHOD":
                    code_structure = (
                        "Class Methods:\n\t"
                        + "\n\t".join([c["signature"] for c in class_methods])
                        + "\n\n"
                    )
                elif code_type == "OTHER":
                    code_structure = (
                        "Other:\n\t"
                        + "\n\t".join([o["signature"] for o in others])
                        + "\n\n"
                    )
            else:
                # Sort the list using the custom sorting key
                sorted_data = sorted(full_metadata_list, key=custom_sorting_key)

                # Iterate through everything and put it into the prompt
                code_structure = "\n\t".join(
                    [f"{m['type']}: {m['signature']}" for m in sorted_data]
                )

            return f"The code structure looks like:\n{code_structure}"

        except Exception as e:
            logging.error(f"Error getting code structure: {e}")
            return f"There was an error getting the code structure: {e}"

    def get_metadata(
        self,
        full_metadata_list,
        modules,
        functions,
        class_methods,
        others,
        document_chunks,
    ):
        for doc in document_chunks:
            if doc.additional_metadata is not None:
                metadata = doc.additional_metadata
                if metadata not in full_metadata_list:
                    full_metadata_list.append(metadata)
                    if metadata["type"] == "MODULE":
                        modules.append(metadata)
                    elif metadata["type"] == "FUNCTION_DEFINITION":
                        functions.append(metadata)
                    elif metadata["type"] == "CLASS_METHOD":
                        class_methods.append(metadata)
                    else:
                        others.append(metadata)

    def get_all_code_in_file(self, target_file_id: int):
        """Useful for getting all of the code in a loaded 'Code' file.  

        Args:
            target_file_id (int): The 'Code' classified file ID you would like to get the full code for.
        """
        documents = Documents()

        file_model = documents.get_file(target_file_id)

        file_data = file_model.file_data.decode("utf-8")
        
        max_code_file_size = self.interaction_manager.tool_kwargs.get('max_code_file_size', 5000)
        if num_tokens_from_string(file_data) > max_code_file_size:
            return f"File '{file_model.file_name}' is too large- please refactor it into a reasonable size!"

        return (
            f"Here is the code for the file with id: '{target_file_id}':\n```\n{file_data}\n```"
        )

    def code_details(
        self,
        target_file_id: int,
        target_signature: str,
    ):
        """Useful for getting the details of a specific signature (signature cannot be blank) in a specific loaded 'Code' file (required: target_file_id).
        
        !! PAY ATTENTION: This tool should only be used if you have a specific code signature you are looking for. Never use it without a signature, or with a blank signature !!

        Don't use this on anything that isn't classified as 'Code'.

        Args:
            target_file_id (int): The 'Code' classified file ID you would like to get the code details for.
            target_signature (str): The signature (e.g. class declaration, function declaration, etc.) of the piece of code you would like to get the details for. 
        """
        documents = Documents()
        code_details = ""

        try:
            target_document_chunk = None            
            if target_file_id:
                file = documents.get_file(target_file_id)

                document_chunks = documents.get_document_chunks_by_file_id(
                    target_file_id
                )

                code_details = f"The code details for {target_signature or file.file_name} is:\n\n"

                if target_signature is None or target_signature == "":
                    return code_details + file.file_data.decode("utf-8")

                # Find the document chunk that matches the target signature
                for doc in document_chunks:
                    if doc.additional_metadata is not None:
                        metadata = doc.additional_metadata
                        if target_signature in metadata["signature"]:
                            target_document_chunk = doc
                            break

            if target_file_id is None or target_document_chunk is None:
                # Sometimes the AI is stupid and gets in here before it has a signature.  Let's try to help it out.
                # Fall back to searching the code file for the signature the AI passed in
                related_documents = documents.search_document_embeddings(
                    target_signature,
                    SearchType.Similarity,
                    self.interaction_manager.collection_id,
                    target_file_id,
                    top_k=self.interaction_manager.tool_kwargs.get("search_top_k", 10),
                )

                full_metadata_list = []
                modules = []
                functions = []
                class_methods = []
                others = []

                self.get_metadata(
                    full_metadata_list,
                    modules,
                    functions,
                    class_methods,
                    others,
                    related_documents,
                )

                # TODO: ... magic number
                # Loop through the full metadata list and add it to the output, checking to see if we're over the arbitrary token limit of 1000
                for doc in related_documents:
                    max_document_chunk_size = self.interaction_manager.tool_kwargs.get('max_document_chunk_size', 1000)
                    if num_tokens_from_string(code_details) > max_document_chunk_size:
                        break
                    metadata = doc.additional_metadata
                    if metadata["type"] != "MODULE":
                        code_details += metadata["text"] + "\n\n"

                # If we still can't find anything, tell the AI it's behaving badly
                return (
                    "I found the following code, but no code exists with that signature!  You were probably being a bad AI and NOT following the instructions where I told you to use the code_structure tool first!  BAD AI!\n\n"
                    + code_details
                )
            else:
                code_details += target_document_chunk.document_text

                return target_document_chunk.document_text  # code_details
        except Exception as e:
            logging.error(f"Error getting code details: {e}")
            return f"There was an error getting the code details: {e}"    

    def create_stub_code(self, file_id: int, available_dependencies: List[str] = None):
        """Create a mock / stub version of the given code file.

        Args:
            file_id: The id of the file to create stubs for.
            available_dependencies: The list of available dependencies for the file.
        """

        documents_helper = Documents()

        documents = documents_helper.get_document_chunks_by_file_id(file_id)

        C_STUBBING_TEMPLATE = get_prompt(
            self.configuration.model_configuration.llm_type, "C_STUBBING_TEMPLATE"
        )

        stub_dependencies_template = get_prompt(
            self.configuration.model_configuration.llm_type,
            "STUB_DEPENDENCIES_TEMPLATE",
        )

        # Loop over all of the document chunks and have the LLM create a fake version of each for us

        if available_dependencies is None:
            stub_dependencies = ""
        else:
            stub_dependencies = stub_dependencies_template.format(
                stub_dependencies="\n".join(available_dependencies)
            )

        # Might want to split this up into chunks??
        # stubbed_code = []
        # for doc in documents:
        #     prompt = C_STUBBING_TEMPLATE.format(
        #         code=doc.document_text,
        #         stub_dependencies_template=stub_dependencies,
        #     )
        #     stubbed_code.append(self.llm.predict(prompt))
        # full_stubbed_code = "\n\n".join(stubbed_code)

        stubbed_code = "Could not stub code, no MODULE type found!"

        for doc in documents:
            if doc.additional_metadata["type"] == "MODULE":
                prompt = C_STUBBING_TEMPLATE.format(
                    code=doc.document_text,
                    stub_dependencies_template=stub_dependencies,
                )
                stubbed_code = self.llm.predict(prompt)
                break

        return {
            "file": doc.document_name,
            "code": f"Stubbed code for {doc.document_name}:\n```\n{stubbed_code}\n```",
        }


# Testing
if __name__ == "__main__":
    code_tool = CodeTool(None, None, None)

    dependency = code_tool.get_dependency_graph(4)

    code_tool.pretty_print_dependency_graph(dependency)

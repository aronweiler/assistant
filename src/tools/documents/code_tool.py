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

from src.tools.documents.code_dependency import CodeDependency


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

    def get_pretty_dependency_graph(self, target_file_id) -> CodeDependency:
        """Get a graph of the dependencies for a given file.

        Args:
            target_file_id: The id of the file to get the dependencies for.
            collection_id: The id of the collection the file is in.
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
            collection_id: The id of the collection the file is in.
        """
        documents = Documents()

        # Get the list of documents
        document_chunks = documents.get_document_chunks_by_file_id(
            target_file_id=target_file_id,
        )

        # Get the list of top-level includes
        code_dependency = CodeDependency(name=document_chunks[0].document_name, dependencies=[])
        for doc in document_chunks:
            if doc.additional_metadata["type"] == "MODULE":
                # This might need to be something other than "includes" at some point
                for include in doc.additional_metadata["includes"]:
                    # strip the filename from the path
                    filename = include.split("/")[-1]
                    if not [d for d in code_dependency.dependencies if d.name == filename] and not filename == code_dependency.name:
                        file = documents.get_file_by_name(filename, self.interaction_manager.collection_id)
                        if file:
                            # Get the dependencies
                            code_dependency.dependencies.append(self.get_dependency_graph(file.id))                            

        return code_dependency
    
    def pretty_print_dependency_graph(self, code_dependency: CodeDependency, indent: int = 0):
        """
        Pretty print the dependency graph in Markdown format.

        Args:
            code_dependency: The dependency graph to print.
            indent: The indent level to use for the print.
        """        
        output = (" " * indent + f"- {code_dependency.name}")
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
        """Useful for understanding the high-level structure of a specific loaded code file.  Use this tool before using the 'code_detail' tool.
        This tool will give you a list of module names, function signatures, and class method signatures.
        You can use the signature of any of these to get more details about that specific piece of code when calling code_detail.

        Don't use this tool on anything that isn't classified as 'Code'.

        Args:
            target_file_id (int): REQUIRED! The file ID you would like to get the code structure for.
            code_type (str, optional): Valid code_type arguments are 'MODULE', 'FUNCTION_DECLARATION', and 'CLASS_METHOD'. When left empty, the code structure will be returned in its entirety.
        """
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

            return f"--- BEGIN CODE STRUCTURE ---\n{code_structure}\n--- END CODE STRUCTURE ---"

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

    def code_details(
        self,
        target_file_id: int,
        target_signature: str,
    ):
        """Useful for getting the details of a specific piece of code in a loaded code file.  Use this tool after using the 'code_structure' tool.  This tool will give you the code details for the specific piece of code you requested.  You can get the signature of any piece of code from the 'code_structure' tool.

        Don't use this on anything that isn't classified as 'Code'.

        Args:
            target_file_id (int): The file ID you would like to get the code details for.
            target_signature (str): The signature of the piece of code you would like to get the details for. Valid values for this argument are the signatures returned by the 'code_structure' tool.
        """
        documents = Documents()

        try:
            document_chunks = documents.get_document_chunks_by_file_id(target_file_id)

            code_details = f"The code details for {target_signature} is:\n\n"

            # Find the document chunk that matches the target signature
            target_document_chunk = None
            for doc in document_chunks:
                if doc.additional_metadata is not None:
                    metadata = doc.additional_metadata
                    if target_signature in metadata["signature"]:
                        target_document_chunk = doc
                        break

            if target_document_chunk is None:
                # Sometimes the AI is stupid and gets in here before it has a signature.  Let's try to help it out.
                # Fall back to searching the code file for the signature the AI passed in
                related_documents = documents.search_document_embeddings(
                    target_signature,
                    SearchType.Similarity,
                    self.interaction_manager.collection_id,
                    target_file_id,
                    top_k=20,  # TODO: ... magic number
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
                    if num_tokens_from_string(code_details) > 1000:
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

    def search_loaded_documents(
        self,        
        original_user_query: str,
        search_query: str = None,
        target_file_id: int = None,
    ):
        """Searches the loaded code files for the given query.  Use this tool when the user is looking for code that isn't in a value returned by code_structure. 
        
        The target_file_id argument is optional, and can be used to search a specific file if the user has specified one.

        IMPORTANT: If the user has not asked you to look in a specific file, don't use target_file_id.

        Args:            
            original_user_query (str, required): The original unmodified query input from the user.
            search_query (str, optional): The query, possibly rephrased by you, to search the files for.
            target_file_id (int, optional): The file_id if you want to search a specific file. Defaults to None which searches all files.
        """
        search_kwargs = {
            "top_k": self.interaction_manager.tool_kwargs.get("search_top_k", 10),
            "search_type": SearchType.Similarity,
            "interaction_id": self.interaction_manager.interaction_id,
            "collection_id": self.interaction_manager.collection_id,
            "target_file_id": target_file_id,
        }

        documents_helper = Documents()

        # Create the documents class for the retriever
        self.pgvector_retriever = PGVectorRetriever(
            vectorstore=documents_helper,
            search_kwargs=search_kwargs,
        )

        qa_chain = LLMChain(
            llm=self.llm,
            prompt=get_prompt(
                self.configuration.model_configuration.llm_type, "CODE_QUESTION_PROMPT"
            ),
            verbose=True,
        )

        qa_with_sources = RetrievalQAWithSourcesChain.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.pgvector_retriever,
            chain_type_kwargs={
                "prompt": get_prompt(
                    self.configuration.model_configuration.llm_type,
                    "CODE_QUESTION_PROMPT",
                )
            },
        )

        combine_chain = StuffDocumentsChain(
            llm_chain=qa_chain,
            document_prompt=get_prompt(
                self.configuration.model_configuration.llm_type, "CODE_PROMPT"
            ),
            document_variable_name="summaries",
        )

        qa_with_sources.combine_documents_chain = combine_chain
        qa_with_sources.return_source_documents = True

        results = qa_with_sources({"question": original_user_query})

        return f"RESULTS: \n{results['answer']}.\n\nThe sources are: {results['sources']}"

    def create_stub_code(self, file_id: int, available_dependencies:List[str] = None):
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
            self.configuration.model_configuration.llm_type, "STUB_DEPENDENCIES_TEMPLATE"
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

    dependency = code_tool.get_dependency_graph(4, 1)

    code_tool.pretty_print_dependency_graph(dependency)

from langchain.tools import StructuredTool


class GenericTool:
    def __init__(
        self,
        display_name,
        description,
        function,
        name=None,
        requires_documents=False,
        help_text=None,
        document_classes=[],
        return_direct=False,
        additional_instructions=None,
        requires_repository=False
    ):
        self.description = description
        self.additional_instructions = additional_instructions
        self.function = function
        self.schema = self.extract_function_schema(function)
        self.schema_name = self.schema["name"]
        self.name = name if name else self.schema["name"]
        self.structured_tool = StructuredTool.from_function(
            func=self.function, return_direct=return_direct, description=description
        )
        self.document_classes = document_classes
        self.display_name = display_name
        self.requires_documents = requires_documents
        self.help_text = help_text if help_text else self.description
        self.requires_repository = requires_repository

    def extract_function_schema(self, func):
        import inspect

        sig = inspect.signature(func)
        parameters = []

        def stringify_annotation(parameter):
            if hasattr(
                parameter.annotation, "__origin__"
            ):  # This checks if it's a special type from typing
                return str(parameter.annotation).replace(
                    "typing.", ""
                )  # Strips the 'typing.' part if present
            elif hasattr(parameter.annotation, "__name__"):
                return parameter.annotation.__name__
            else:
                return str(parameter.annotation)

        for param_name, param in sig.parameters.items():
            param_info = {
                "argument_name": param_name,
                "argument_type": stringify_annotation(param),
                "required": "optional"
                if param.default != inspect.Parameter.empty
                else "required",
            }
            parameters.append(param_info)

        schema = {"name": func.__name__, "parameters": parameters}

        return schema

import enum


@enum.unique
class NodeType(enum.Enum):
    UNKNOWN = 'unknown'
    CLASS_METHOD = 'class_method'
    FUNCTION_DEFINITION = 'function_definition'
    MODULE = 'module'
    CLASS_DEFINITION = 'class_definition'
    STRUCT_DEFINITION = 'struct_definition'
    PREPROCESSING_DIRECTIVE = 'preprocessing_directive'

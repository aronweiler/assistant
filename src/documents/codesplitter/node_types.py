
import enum


@enum.unique
class NodeType(enum.Enum):
    UNKNOWN = 'unknown'
    CLASS = 'class'
    CLASS_METHOD = 'class_method'
    FUNCTION_DEFINITION = 'function_definition'
    INCLUDE = 'include'
    MODULE = 'module'
    PREPROCESSING_DIRECTIVE = 'preprocessing_directive'

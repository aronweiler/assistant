
import enum


@enum.unique
class NodeType(enum.Enum):
    UNKNOWN = 'unknown'
    CLASS_METHOD = 'class_method'
    FUNCTION_DEFINITION = 'function_definition'
    MODULE = 'module'

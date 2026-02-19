"""Property type for document metadata filtering."""

from enum import StrEnum


class PropertyType(StrEnum):
    """Supported property value types for filtering."""

    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    DATE = "date"

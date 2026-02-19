"""Property entity - document metadata key-value with type."""

from dataclasses import dataclass
from uuid import UUID

from relrag.domain.value_objects import PropertyType


@dataclass
class Property:
    """Property - key-value metadata for a document with type for filtering."""

    document_id: UUID
    key: str
    value: str
    property_type: PropertyType

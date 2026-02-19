"""Property repository port - document metadata."""

from typing import Protocol
from uuid import UUID

from relrag.domain.entities import Property
from relrag.domain.value_objects import PropertyType


class PropertySchemaItem:
    """Key, type and optional distinct values for one property in a collection."""

    def __init__(
        self,
        key: str,
        property_type: PropertyType,
        values: list[str] | None = None,
    ) -> None:
        self.key = key
        self.property_type = property_type
        self.values = values or []


class PropertyRepository(Protocol):
    """Port for document property persistence."""

    async def list_by_document(self, document_id: UUID) -> list[Property]: ...

    async def create_batch(self, properties: list[Property]) -> None: ...

    async def delete_by_document(self, document_id: UUID) -> None: ...

    async def list_schema_by_collection(
        self, collection_id: UUID
    ) -> list[PropertySchemaItem]: ...

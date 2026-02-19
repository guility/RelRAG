"""Property repository port - document metadata."""

from typing import Protocol
from uuid import UUID

from relrag.domain.entities import Property


class PropertyRepository(Protocol):
    """Port for document property persistence."""

    async def list_by_document(self, document_id: UUID) -> list[Property]: ...

    async def create_batch(self, properties: list[Property]) -> None: ...

    async def delete_by_document(self, document_id: UUID) -> None: ...

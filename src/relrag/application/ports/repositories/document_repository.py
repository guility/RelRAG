"""Document repository port."""

from typing import Protocol
from uuid import UUID

from relrag.domain.entities import Document


class DocumentRepository(Protocol):
    """Port for document persistence."""

    async def get_by_id(
        self, document_id: UUID, include_deleted: bool = False
    ) -> Document | None: ...

    async def get_by_source_hash(self, source_hash: bytes) -> Document | None: ...

    async def list(
        self,
        *,
        cursor: str | None = None,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[Document], str | None]: ...

    async def create(self, document: Document) -> Document: ...

    async def update(self, document: Document) -> Document: ...

    async def soft_delete(self, document_id: UUID) -> None: ...

    async def hard_delete(self, document_id: UUID) -> None: ...

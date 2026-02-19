"""Pack repository port."""

from typing import Protocol
from uuid import UUID

from relrag.domain.entities import Pack


class PackRepository(Protocol):
    """Port for pack persistence."""

    async def get_by_id(self, pack_id: UUID, include_deleted: bool = False) -> Pack | None: ...

    async def list(
        self,
        *,
        document_id: UUID | None = None,
        collection_id: UUID | None = None,
        cursor: str | None = None,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[Pack], str | None]: ...

    async def create(self, pack: Pack) -> Pack: ...

    async def update(self, pack: Pack) -> None: ...

    async def soft_delete(self, pack_id: UUID) -> None: ...

    async def hard_delete(self, pack_id: UUID) -> None: ...

    async def add_to_collection(self, pack_id: UUID, collection_id: UUID) -> None: ...

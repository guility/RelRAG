"""Collection repository port."""

from typing import Protocol
from uuid import UUID

from relrag.domain.entities import Collection


class CollectionRepository(Protocol):
    """Port for collection persistence."""

    async def get_by_id(
        self, collection_id: UUID, include_deleted: bool = False
    ) -> Collection | None: ...

    async def list(
        self,
        *,
        cursor: str | None = None,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[Collection], str | None]: ...

    async def create(self, collection: Collection) -> Collection: ...

    async def update(self, collection: Collection) -> None: ...

    async def soft_delete(self, collection_id: UUID) -> None: ...

    async def hard_delete(self, collection_id: UUID) -> None: ...

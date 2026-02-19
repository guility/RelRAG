"""Chunk repository port."""

from typing import Protocol
from uuid import UUID

from relrag.domain.entities import Chunk


class ChunkRepository(Protocol):
    """Port for chunk persistence."""

    async def create_batch(self, chunks: list[Chunk]) -> list[Chunk]: ...

    async def delete_by_pack_id(self, pack_id: UUID) -> None: ...

    async def get_by_pack_id(self, pack_id: UUID) -> list[Chunk]: ...

    async def search(
        self,
        collection_id: UUID,
        query_embedding: list[float],
        query_fts: str | None = None,
        vector_weight: float = 0.7,
        fts_weight: float = 0.3,
        limit: int = 10,
        property_filters: dict[str, str] | None = None,
    ) -> list[dict[str, object]]: ...

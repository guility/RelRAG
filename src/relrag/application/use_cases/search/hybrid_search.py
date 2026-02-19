"""Hybrid search use case - vector + full-text."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from relrag.application.ports import EmbeddingProvider, PermissionChecker
from relrag.domain.exceptions import PermissionDenied
from relrag.domain.value_objects import PermissionAction


@dataclass
class HybridSearchResult:
    """Single search result."""

    chunk_id: UUID
    pack_id: UUID
    content: str
    score: float


@dataclass
class HybridSearchInput:
    """Input for hybrid search."""

    collection_id: UUID
    query: str
    vector_weight: float = 0.7
    fts_weight: float = 0.3
    limit: int = 10
    filters: dict[str, Any] | None = None  # key -> { gte?, lte?, one_of?, eq? }


class HybridSearchUseCase:
    """Hybrid search: vector similarity + full-text with configurable weights."""

    def __init__(
        self,
        unit_of_work_factory: type,
        permission_checker: PermissionChecker,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._uow_factory = unit_of_work_factory
        self._permission_checker = permission_checker
        self._embedding_provider = embedding_provider

    async def execute(
        self, user_id: str, input_data: HybridSearchInput
    ) -> list[HybridSearchResult]:
        """Execute hybrid search."""
        has_read = await self._permission_checker.check(
            user_id, input_data.collection_id, PermissionAction.READ
        )
        if not has_read:
            raise PermissionDenied("User does not have read access to collection")

        query_embedding = await self._embedding_provider.embed([input_data.query])
        embedding = query_embedding[0] if query_embedding else []

        async with self._uow_factory() as uow:
            results = await uow.chunks.search(
                collection_id=input_data.collection_id,
                query_embedding=embedding,
                query_fts=input_data.query,
                vector_weight=input_data.vector_weight,
                fts_weight=input_data.fts_weight,
                limit=input_data.limit,
                property_filters=input_data.filters,
            )
            return [
                HybridSearchResult(
                    chunk_id=r["chunk_id"],
                    pack_id=r["pack_id"],
                    content=r["content"],
                    score=r["score"],
                )
                for r in results
            ]

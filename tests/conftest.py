"""Pytest fixtures for RelRAG tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from relrag.application.dto.chunking_config import ChunkingConfig
from relrag.domain.entities import (
    Chunk,
    Collection,
    Configuration,
    Document,
    Pack,
    Permission,
    Property,
    Role,
)
from relrag.domain.value_objects import ChunkingStrategy


# --- Fake repositories ---


class FakeDocumentRepository:
    """In-memory document repository."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, Document] = {}
        self._by_hash: dict[bytes, Document] = {}

    async def get_by_id(
        self, document_id: UUID, include_deleted: bool = False
    ) -> Document | None:
        doc = self._by_id.get(document_id)
        if not doc or (not include_deleted and doc.deleted_at):
            return None
        return doc

    async def get_by_source_hash(self, source_hash: bytes) -> Document | None:
        return self._by_hash.get(source_hash)

    async def list(
        self,
        *,
        cursor: str | None = None,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[Document], str | None]:
        items = [
            d
            for d in self._by_id.values()
            if include_deleted or d.deleted_at is None
        ]
        items.sort(key=lambda d: d.id)
        start = 0
        if cursor:
            try:
                cursor_uuid = UUID(cursor)
                for i, d in enumerate(items):
                    if d.id > cursor_uuid:
                        start = i
                        break
            except ValueError:
                pass
        page = items[start : start + limit + 1]
        next_cursor = str(page[limit].id) if len(page) > limit else None
        return (page[:limit], next_cursor)

    async def create(self, document: Document) -> Document:
        self._by_id[document.id] = document
        self._by_hash[document.source_hash] = document
        return document

    async def update(self, document: Document) -> Document:
        self._by_id[document.id] = document
        self._by_hash[document.source_hash] = document
        return document

    async def soft_delete(self, document_id: UUID) -> None:
        doc = self._by_id.get(document_id)
        if doc:
            from dataclasses import replace

            self._by_id[document_id] = replace(doc, deleted_at=datetime.now(UTC))

    async def hard_delete(self, document_id: UUID) -> None:
        doc = self._by_id.pop(document_id, None)
        if doc:
            self._by_hash.pop(doc.source_hash, None)


class FakePackRepository:
    """In-memory pack repository with pack_collection M:N."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, Pack] = {}
        self._pack_collections: dict[UUID, set[UUID]] = {}  # pack_id -> {collection_id}

    async def get_by_id(self, pack_id: UUID, include_deleted: bool = False) -> Pack | None:
        pack = self._by_id.get(pack_id)
        if not pack or (not include_deleted and pack.deleted_at):
            return None
        return pack

    async def list(
        self,
        *,
        document_id: UUID | None = None,
        collection_id: UUID | None = None,
        cursor: str | None = None,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[Pack], str | None]:
        items = list(self._by_id.values())
        if not include_deleted:
            items = [p for p in items if p.deleted_at is None]
        if document_id:
            items = [p for p in items if p.document_id == document_id]
        if collection_id:
            items = [
                p
                for p in items
                if collection_id in self._pack_collections.get(p.id, set())
            ]
        items.sort(key=lambda p: p.id)
        start = 0
        if cursor:
            try:
                cursor_uuid = UUID(cursor)
                for i, p in enumerate(items):
                    if p.id > cursor_uuid:
                        start = i
                        break
            except ValueError:
                pass
        page = items[start : start + limit + 1]
        next_cursor = str(page[limit].id) if len(page) > limit else None
        return (page[:limit], next_cursor)

    async def create(self, pack: Pack) -> Pack:
        self._by_id[pack.id] = pack
        self._pack_collections.setdefault(pack.id, set())
        return pack

    async def update(self, pack: Pack) -> None:
        self._by_id[pack.id] = pack

    async def soft_delete(self, pack_id: UUID) -> None:
        pack = self._by_id.get(pack_id)
        if pack:
            from dataclasses import replace

            self._by_id[pack_id] = replace(pack, deleted_at=datetime.now(UTC))

    async def hard_delete(self, pack_id: UUID) -> None:
        self._by_id.pop(pack_id, None)
        self._pack_collections.pop(pack_id, None)

    async def add_to_collection(self, pack_id: UUID, collection_id: UUID) -> None:
        self._pack_collections.setdefault(pack_id, set()).add(collection_id)


class FakeChunkRepository:
    """In-memory chunk repository."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, Chunk] = {}
        self._by_pack: dict[UUID, list[Chunk]] = {}
        self._search_results: list[dict] = []

    def set_search_results(self, results: list[dict]) -> None:
        """Set predefined search results for testing."""
        self._search_results = results

    async def create_batch(self, chunks: list[Chunk]) -> list[Chunk]:
        for c in chunks:
            self._by_id[c.id] = c
            self._by_pack.setdefault(c.pack_id, []).append(c)
            self._by_pack[c.pack_id].sort(key=lambda x: x.position)
        return chunks

    async def delete_by_pack_id(self, pack_id: UUID) -> None:
        for c in self._by_pack.get(pack_id, []):
            self._by_id.pop(c.id, None)
        self._by_pack.pop(pack_id, None)

    async def get_by_pack_id(self, pack_id: UUID) -> list[Chunk]:
        return sorted(
            self._by_pack.get(pack_id, []),
            key=lambda c: c.position,
        )

    async def search(
        self,
        collection_id: UUID,
        query_embedding: list[float],
        query_fts: str | None = None,
        vector_weight: float = 0.7,
        fts_weight: float = 0.3,
        limit: int = 10,
        property_filters: dict[str, str] | None = None,
    ) -> list[dict]:
        return self._search_results[:limit]


class FakeConfigurationRepository:
    """In-memory configuration repository."""

    def __init__(self, collections_repo: "FakeCollectionRepository | None" = None) -> None:
        self._by_id: dict[UUID, Configuration] = {}
        self._by_collection: dict[UUID, Configuration] = {}
        self._collections_repo = collections_repo

    async def get_by_id(self, configuration_id: UUID) -> Configuration | None:
        return self._by_id.get(configuration_id)

    async def get_by_collection_id(self, collection_id: UUID) -> Configuration | None:
        if collection_id in self._by_collection:
            return self._by_collection[collection_id]
        if self._collections_repo:
            coll = await self._collections_repo.get_by_id(collection_id)
            if coll:
                return self._by_id.get(coll.configuration_id)
        return None

    async def list(
        self,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Configuration], str | None]:
        items = sorted(self._by_id.values(), key=lambda c: c.id)
        start = 0
        if cursor:
            try:
                cursor_uuid = UUID(cursor)
                for i, c in enumerate(items):
                    if c.id > cursor_uuid:
                        start = i
                        break
            except ValueError:
                pass
        page = items[start : start + limit + 1]
        next_cursor = str(page[limit].id) if len(page) > limit else None
        return (page[:limit], next_cursor)

    async def create(self, configuration: Configuration) -> Configuration:
        self._by_id[configuration.id] = configuration
        return configuration

    def add_for_collection(self, collection_id: UUID, config: Configuration) -> None:
        """Helper to associate config with collection (for tests)."""
        self._by_id[config.id] = config
        self._by_collection[collection_id] = config


class FakeCollectionRepository:
    """In-memory collection repository."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, Collection] = {}

    async def get_by_id(
        self, collection_id: UUID, include_deleted: bool = False
    ) -> Collection | None:
        coll = self._by_id.get(collection_id)
        if not coll or (not include_deleted and coll.deleted_at):
            return None
        return coll

    async def list(
        self,
        *,
        cursor: str | None = None,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[Collection], str | None]:
        items = [
            c
            for c in self._by_id.values()
            if include_deleted or c.deleted_at is None
        ]
        items.sort(key=lambda c: c.id)
        start = 0
        if cursor:
            try:
                cursor_uuid = UUID(cursor)
                for i, c in enumerate(items):
                    if c.id > cursor_uuid:
                        start = i
                        break
            except ValueError:
                pass
        page = items[start : start + limit + 1]
        next_cursor = str(page[limit].id) if len(page) > limit else None
        return (page[:limit], next_cursor)

    async def list_by_subject(
        self,
        subject: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Collection], str | None]:
        """List collections where subject has permission. Delegates to list for fake."""
        return await self.list(cursor=cursor, limit=limit, include_deleted=False)

    async def create(self, collection: Collection) -> Collection:
        self._by_id[collection.id] = collection
        return collection

    async def update(self, collection: Collection) -> None:
        self._by_id[collection.id] = collection

    async def soft_delete(self, collection_id: UUID) -> None:
        coll = self._by_id.get(collection_id)
        if coll:
            from dataclasses import replace

            self._by_id[collection_id] = replace(
                coll, deleted_at=datetime.now(UTC)
            )

    async def hard_delete(self, collection_id: UUID) -> None:
        self._by_id.pop(collection_id, None)


class FakePermissionRepository:
    """In-memory permission repository."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, Permission] = {}

    async def get_by_id(self, permission_id: UUID) -> Permission | None:
        return self._by_id.get(permission_id)

    async def list_by_collection(self, collection_id: UUID) -> list[Permission]:
        return [
            p
            for p in self._by_id.values()
            if p.collection_id == collection_id
        ]

    async def list_by_subject(self, subject: str) -> list[Permission]:
        return [p for p in self._by_id.values() if p.subject == subject]

    async def get_for_collection(
        self, collection_id: UUID, subject: str
    ) -> Permission | None:
        for p in self._by_id.values():
            if p.collection_id == collection_id and p.subject == subject:
                return p
        return None

    async def create(self, permission: Permission) -> Permission:
        self._by_id[permission.id] = permission
        return permission

    async def update(self, permission: Permission) -> None:
        self._by_id[permission.id] = permission

    async def delete(self, permission_id: UUID) -> None:
        self._by_id.pop(permission_id, None)


class FakeRoleRepository:
    """In-memory role repository."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, Role] = {}
        self._by_name: dict[str, Role] = {}

    async def get_by_id(self, role_id: UUID) -> Role | None:
        return self._by_id.get(role_id)

    async def get_by_name(self, name: str) -> Role | None:
        return self._by_name.get(name)

    async def list_all(self) -> list[Role]:
        return list(self._by_id.values())

    async def get_actions_for_role(self, role_id: UUID) -> list[str]:
        role = self._by_id.get(role_id)
        if role and role.name == "admin":
            return ["read", "write", "admin", "migrate"]
        if role and role.name == "editor":
            return ["read", "write"]
        if role and role.name == "viewer":
            return ["read"]
        return []

    def add_role(self, role: Role) -> None:
        """Helper to add role for tests."""
        self._by_id[role.id] = role
        self._by_name[role.name] = role


class FakePropertyRepository:
    """In-memory property repository."""

    def __init__(self) -> None:
        self._store: list[Property] = []

    async def list_by_document(self, document_id: UUID) -> list[Property]:
        return [p for p in self._store if p.document_id == document_id]

    async def create_batch(self, properties: list[Property]) -> None:
        self._store.extend(properties)

    async def delete_by_document(self, document_id: UUID) -> None:
        self._store = [p for p in self._store if p.document_id != document_id]


# --- Fake UnitOfWork ---


class FakeUnitOfWork:
    """In-memory Unit of Work with fake repositories."""

    def __init__(self) -> None:
        self.documents = FakeDocumentRepository()
        self.packs = FakePackRepository()
        self.chunks = FakeChunkRepository()
        self.collections = FakeCollectionRepository()
        self.configurations = FakeConfigurationRepository(
            collections_repo=self.collections
        )
        self.permissions = FakePermissionRepository()
        self.roles = FakeRoleRepository()
        self.properties = FakePropertyRepository()

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


@asynccontextmanager
async def fake_uow_factory() -> AsyncIterator[FakeUnitOfWork]:
    """Factory that yields a fresh FakeUnitOfWork per call."""
    uow = FakeUnitOfWork()
    yield uow


# --- Fixtures ---


@pytest.fixture
def fake_uow() -> FakeUnitOfWork:
    """Fresh in-memory UnitOfWork for each test."""
    return FakeUnitOfWork()


@pytest.fixture
def uow_factory():
    """Factory returning async context manager with FakeUnitOfWork."""

    @asynccontextmanager
    async def _factory():
        uow = FakeUnitOfWork()
        yield uow

    return _factory


@pytest.fixture
def mock_permission_checker():
    """AsyncMock for PermissionChecker - returns True by default."""
    from unittest.mock import AsyncMock

    mock = AsyncMock()
    mock.check.return_value = True
    return mock


@pytest.fixture
def mock_embedding_provider():
    """AsyncMock for EmbeddingProvider - returns fixed vectors per text."""

    async def _embed(texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1536 for _ in texts]

    from unittest.mock import AsyncMock

    mock = AsyncMock()
    mock.embed = AsyncMock(side_effect=_embed)
    return mock


@pytest.fixture
def chunking_config() -> ChunkingConfig:
    """Default chunking config for RecursiveChunker tests."""
    return ChunkingConfig(
        chunk_size=100,
        chunk_overlap=20,
        strategy=ChunkingStrategy.RECURSIVE,
    )


def pytest_collection_modifyitems(items: list) -> None:
    """Run e2e tests last so Playwright's event loop does not break sync Falcon tests."""
    e2e, other = [], []
    for item in items:
        if "/e2e/" in item.nodeid or "\\e2e\\" in item.nodeid:
            e2e.append(item)
        else:
            other.append(item)
    if e2e:
        items[:] = other + e2e

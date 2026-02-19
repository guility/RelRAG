"""Unit tests for use cases."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from relrag.application.dto.document_dto import DocumentCreateInput
from relrag.application.use_cases.collection.create_collection import (
    CreateCollectionUseCase,
)
from relrag.application.use_cases.collection.migrate_collection import (
    MigrateCollectionUseCase,
)
from relrag.application.use_cases.document.get_document import GetDocumentUseCase
from relrag.application.use_cases.document.load_document import LoadDocumentUseCase
from relrag.application.use_cases.permission.assign_permission import (
    AssignPermissionUseCase,
)
from relrag.application.use_cases.permission.revoke_permission import (
    RevokePermissionUseCase,
)
from relrag.application.use_cases.search.hybrid_search import (
    HybridSearchInput,
    HybridSearchUseCase,
)
from relrag.domain.entities import (
    Collection,
    Configuration,
    Document,
    Pack,
    Permission,
    Role,
)
from relrag.domain.exceptions import NotFound, PermissionDenied
from relrag.domain.value_objects import ChunkingStrategy
from relrag.infrastructure.chunking.recursive_chunker import RecursiveChunker

from tests.conftest import FakeUnitOfWork


# --- CreateCollectionUseCase ---


def _make_create_collection_factory(config_id, has_admin_role=True):
    """Build UoW factory (async context manager) with config and optional admin role."""
    admin_role = Role(
        id=uuid4(),
        name="admin",
        description="Administrator",
    )

    @asynccontextmanager
    async def factory():
        uow = FakeUnitOfWork()
        uow.configurations._by_id[config_id] = Configuration(
            id=config_id,
            chunking_strategy=ChunkingStrategy.RECURSIVE,
            embedding_model="text-embedding-3-small",
            embedding_dimensions=1536,
            chunk_size=500,
            chunk_overlap=50,
        )
        if has_admin_role:
            uow.roles.add_role(admin_role)
        yield uow

    return factory


@pytest.mark.asyncio
async def test_create_collection_success() -> None:
    """CreateCollectionUseCase creates collection and assigns admin to creator."""
    config_id = uuid4()
    factory = _make_create_collection_factory(config_id=config_id)
    use_case = CreateCollectionUseCase(unit_of_work_factory=factory)

    collection = await use_case.execute(user_id="user-1", configuration_id=config_id)

    assert collection.id is not None
    assert collection.configuration_id == config_id
    assert collection.deleted_at is None


@pytest.mark.asyncio
async def test_create_collection_not_found_config() -> None:
    """CreateCollectionUseCase raises NotFound when configuration does not exist."""
    config_id = uuid4()

    @asynccontextmanager
    async def empty_factory():
        yield FakeUnitOfWork()

    use_case = CreateCollectionUseCase(unit_of_work_factory=empty_factory)

    with pytest.raises(NotFound, match="Configuration"):
        await use_case.execute(user_id="user-1", configuration_id=config_id)


@pytest.mark.asyncio
async def test_create_collection_not_found_admin_role() -> None:
    """CreateCollectionUseCase raises NotFound when admin role does not exist."""
    config_id = uuid4()
    factory = _make_create_collection_factory(
        config_id=config_id, has_admin_role=False
    )
    use_case = CreateCollectionUseCase(unit_of_work_factory=factory)

    with pytest.raises(NotFound, match="admin"):
        await use_case.execute(user_id="user-1", configuration_id=config_id)


# --- LoadDocumentUseCase ---


def _load_document_uow_factory(collection_id=None, has_config=True):
    """Build UoW factory with config for LoadDocumentUseCase."""
    collection_id = collection_id or uuid4()
    config = Configuration(
        id=uuid4(),
        chunking_strategy=ChunkingStrategy.RECURSIVE,
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        chunk_size=100,
        chunk_overlap=20,
    )

    @asynccontextmanager
    async def factory():
        uow = FakeUnitOfWork()
        if has_config:
            uow.configurations._by_id[config.id] = config
            uow.configurations._by_collection[collection_id] = config
        yield uow

    return factory, collection_id


@pytest.mark.asyncio
async def test_load_document_permission_denied(
    mock_embedding_provider,
) -> None:
    """LoadDocumentUseCase raises PermissionDenied when user has no write access."""
    from unittest.mock import AsyncMock

    factory, collection_id = _load_document_uow_factory()
    perm_checker = AsyncMock()
    perm_checker.check.return_value = False

    use_case = LoadDocumentUseCase(
        unit_of_work_factory=factory,
        permission_checker=perm_checker,
        chunker=RecursiveChunker(),
        embedding_provider=mock_embedding_provider,
    )

    input_data = DocumentCreateInput(
        collection_id=collection_id,
        content="test content",
        properties={},
    )

    with pytest.raises(PermissionDenied, match="write access"):
        await use_case.execute(user_id="user-1", input_data=input_data)


@pytest.mark.asyncio
async def test_load_document_success(
    mock_permission_checker,
    mock_embedding_provider,
) -> None:
    """LoadDocumentUseCase loads document and creates chunks."""
    factory, collection_id = _load_document_uow_factory(collection_id=uuid4())
    use_case = LoadDocumentUseCase(
        unit_of_work_factory=factory,
        permission_checker=mock_permission_checker,
        chunker=RecursiveChunker(),
        embedding_provider=mock_embedding_provider,
    )

    content = "This is a test document with enough text to be chunked."
    input_data = DocumentCreateInput(
        collection_id=collection_id,
        content=content,
        properties={"author": ("Alice", "string")},
    )

    result = await use_case.execute(user_id="user-1", input_data=input_data)

    assert result.id is not None
    assert result.content == content
    assert result.source_hash is not None
    assert result.deleted_at is None


@pytest.mark.asyncio
async def test_load_document_deduplication(
    mock_permission_checker,
    mock_embedding_provider,
) -> None:
    """LoadDocumentUseCase returns existing document when source_hash matches."""
    import hashlib

    collection_id = uuid4()
    factory, _ = _load_document_uow_factory(collection_id=collection_id)
    content = "Duplicate content"
    source_hash = hashlib.md5(content.encode()).digest()

    # Pre-create document and pack in UoW
    uow = FakeUnitOfWork()
    config = Configuration(
        id=uuid4(),
        chunking_strategy=ChunkingStrategy.RECURSIVE,
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        chunk_size=100,
        chunk_overlap=20,
    )
    uow.configurations._by_id[config.id] = config
    uow.configurations._by_collection[collection_id] = config

    now = datetime.now(UTC)
    doc_id = uuid4()
    pack_id = uuid4()
    doc = Document(
        id=doc_id,
        content=content,
        source_hash=source_hash,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    pack = Pack(
        id=pack_id,
        document_id=doc_id,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    await uow.documents.create(doc)
    await uow.packs.create(pack)
    await uow.packs.add_to_collection(pack_id, collection_id)

    @asynccontextmanager
    async def factory_with_data():
        yield uow

    use_case = LoadDocumentUseCase(
        unit_of_work_factory=factory_with_data,
        permission_checker=mock_permission_checker,
        chunker=RecursiveChunker(),
        embedding_provider=mock_embedding_provider,
    )

    input_data = DocumentCreateInput(
        collection_id=collection_id,
        content=content,
        properties={},
        source_hash=source_hash,
    )

    result = await use_case.execute(user_id="user-1", input_data=input_data)

    assert result.id == doc_id
    assert result.content == content
    # Embedding provider should not have been called (dedup path)
    mock_embedding_provider.embed.assert_not_called()


# --- GetDocumentUseCase ---


def _get_document_uow_factory(
    document_id=None, collection_id=None, has_pack_in_collection=True
):
    """Build UoW factory with document and pack for GetDocumentUseCase."""
    doc_id = document_id or uuid4()
    coll_id = collection_id or uuid4()
    now = datetime.now(UTC)
    doc = Document(
        id=doc_id,
        content="test",
        source_hash=b"abc123",
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    pack = Pack(
        id=uuid4(),
        document_id=doc_id,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )

    @asynccontextmanager
    async def factory():
        uow = FakeUnitOfWork()
        await uow.documents.create(doc)
        await uow.packs.create(pack)
        if has_pack_in_collection:
            await uow.packs.add_to_collection(pack.id, coll_id)
        yield uow

    return factory, doc_id, coll_id


@pytest.mark.asyncio
async def test_get_document_permission_denied() -> None:
    """GetDocumentUseCase raises PermissionDenied when user has no read access."""
    from unittest.mock import AsyncMock

    factory, doc_id, coll_id = _get_document_uow_factory()
    perm_checker = AsyncMock()
    perm_checker.check.return_value = False

    use_case = GetDocumentUseCase(
        unit_of_work_factory=factory,
        permission_checker=perm_checker,
    )

    with pytest.raises(PermissionDenied, match="read access"):
        await use_case.execute(
            user_id="user-1",
            document_id=doc_id,
            collection_id=coll_id,
        )


@pytest.mark.asyncio
async def test_get_document_success(
    mock_permission_checker,
) -> None:
    """GetDocumentUseCase returns document when it exists in collection."""
    factory, doc_id, coll_id = _get_document_uow_factory()

    use_case = GetDocumentUseCase(
        unit_of_work_factory=factory,
        permission_checker=mock_permission_checker,
    )

    result = await use_case.execute(
        user_id="user-1",
        document_id=doc_id,
        collection_id=coll_id,
    )

    assert result.id == doc_id
    assert result.content == "test"


@pytest.mark.asyncio
async def test_get_document_not_found(
    mock_permission_checker,
) -> None:
    """GetDocumentUseCase raises NotFound when document does not exist."""
    factory, _, coll_id = _get_document_uow_factory()
    use_case = GetDocumentUseCase(
        unit_of_work_factory=factory,
        permission_checker=mock_permission_checker,
    )

    with pytest.raises(NotFound, match="Document"):
        await use_case.execute(
            user_id="user-1",
            document_id=uuid4(),  # Non-existent
            collection_id=coll_id,
        )


# --- HybridSearchUseCase ---


def _hybrid_search_uow_factory(collection_id=None, search_results=None):
    """Build UoW factory with predefined search results."""
    coll_id = collection_id or uuid4()
    results = search_results or [
        {
            "chunk_id": uuid4(),
            "pack_id": uuid4(),
            "document_id": uuid4(),
            "content": "relevant chunk",
            "vector_score": 0.9,
            "fts_score": 0.5,
            "score": 0.95,
            "doc_props": None,
        }
    ]

    @asynccontextmanager
    async def factory():
        uow = FakeUnitOfWork()
        uow.chunks.set_search_results(results)
        yield uow

    return factory, coll_id


@pytest.mark.asyncio
async def test_hybrid_search_permission_denied(
    mock_embedding_provider,
) -> None:
    """HybridSearchUseCase raises PermissionDenied when user has no read access."""
    from unittest.mock import AsyncMock

    factory, coll_id = _hybrid_search_uow_factory()
    perm_checker = AsyncMock()
    perm_checker.check.return_value = False

    use_case = HybridSearchUseCase(
        unit_of_work_factory=factory,
        permission_checker=perm_checker,
        embedding_provider=mock_embedding_provider,
    )

    with pytest.raises(PermissionDenied, match="read access"):
        await use_case.execute(
            user_id="user-1",
            input_data=HybridSearchInput(collection_id=coll_id, query="test"),
        )


@pytest.mark.asyncio
async def test_hybrid_search_success(
    mock_permission_checker,
    mock_embedding_provider,
) -> None:
    """HybridSearchUseCase returns search results."""
    chunk_id = uuid4()
    pack_id = uuid4()
    doc_id = uuid4()
    factory, coll_id = _hybrid_search_uow_factory(
        search_results=[
            {
                "chunk_id": chunk_id,
                "pack_id": pack_id,
                "document_id": doc_id,
                "content": "found content",
                "vector_score": 0.8,
                "fts_score": 0.4,
                "score": 0.88,
                "doc_props": {"title": "Test Doc", "author": "Tester"},
            }
        ]
    )

    use_case = HybridSearchUseCase(
        unit_of_work_factory=factory,
        permission_checker=mock_permission_checker,
        embedding_provider=mock_embedding_provider,
    )

    results = await use_case.execute(
        user_id="user-1",
        input_data=HybridSearchInput(collection_id=coll_id, query="search"),
    )

    assert len(results) == 1
    assert results[0].chunk_id == chunk_id
    assert results[0].pack_id == pack_id
    assert results[0].document_id == doc_id
    assert results[0].content == "found content"
    assert results[0].vector_score == 0.8
    assert results[0].fts_score == 0.4
    assert results[0].score == 0.88
    assert results[0].document_title == "Test Doc"
    assert results[0].metadata == {"author": "Tester"}


# --- MigrateCollectionUseCase ---


def _migrate_uow_factory(collection_id, new_config_id, packs_with_docs):
    """Build UoW with collection, configs, packs, documents for migrate."""
    now = datetime.now(UTC)
    coll = Collection(
        id=collection_id,
        configuration_id=uuid4(),  # old config
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    new_config = Configuration(
        id=new_config_id,
        chunking_strategy=ChunkingStrategy.RECURSIVE,
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        chunk_size=50,
        chunk_overlap=10,
    )

    @asynccontextmanager
    async def factory():
        uow = FakeUnitOfWork()
        uow.collections._by_id[collection_id] = coll
        uow.configurations._by_id[new_config_id] = new_config
        for doc, pack in packs_with_docs:
            await uow.documents.create(doc)
            await uow.packs.create(pack)
            await uow.packs.add_to_collection(pack.id, collection_id)
        yield uow

    return factory


@pytest.mark.asyncio
async def test_migrate_collection_permission_denied(
    mock_embedding_provider,
) -> None:
    """MigrateCollectionUseCase raises PermissionDenied when user has no migrate access."""
    from unittest.mock import AsyncMock

    coll_id = uuid4()
    config_id = uuid4()
    now = datetime.now(UTC)
    doc = Document(
        id=uuid4(),
        content="x",
        source_hash=b"a" * 16,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    pack = Pack(
        id=uuid4(),
        document_id=doc.id,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    factory = _migrate_uow_factory(coll_id, config_id, [(doc, pack)])
    perm_checker = AsyncMock()
    perm_checker.check.return_value = False

    use_case = MigrateCollectionUseCase(
        unit_of_work_factory=factory,
        permission_checker=perm_checker,
        chunker=RecursiveChunker(),
        embedding_provider=mock_embedding_provider,
    )

    with pytest.raises(PermissionDenied, match="migrate"):
        await use_case.execute("user-1", coll_id, config_id)


@pytest.mark.asyncio
async def test_migrate_collection_success(
    mock_permission_checker,
    mock_embedding_provider,
) -> None:
    """MigrateCollectionUseCase re-chunks and re-embeds documents."""
    coll_id = uuid4()
    config_id = uuid4()
    now = datetime.now(UTC)
    doc = Document(
        id=uuid4(),
        content="Hello world test content for chunking.",
        source_hash=b"a" * 16,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    pack = Pack(
        id=uuid4(),
        document_id=doc.id,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    factory = _migrate_uow_factory(coll_id, config_id, [(doc, pack)])

    use_case = MigrateCollectionUseCase(
        unit_of_work_factory=factory,
        permission_checker=mock_permission_checker,
        chunker=RecursiveChunker(),
        embedding_provider=mock_embedding_provider,
    )

    count = await use_case.execute("user-1", coll_id, config_id)

    assert count == 1


# --- AssignPermissionUseCase ---


def _assign_permission_uow_factory(collection_id, has_role=True, has_existing=False):
    """Build UoW for AssignPermissionUseCase."""
    admin_role = Role(id=uuid4(), name="admin", description="Admin")
    viewer_role = Role(id=uuid4(), name="viewer", description="Viewer")

    @asynccontextmanager
    async def factory():
        uow = FakeUnitOfWork()
        if has_role:
            uow.roles.add_role(admin_role)
            uow.roles.add_role(viewer_role)
        if has_existing:
            perm = Permission(
                id=uuid4(),
                collection_id=collection_id,
                subject="user-2",
                role_id=viewer_role.id,
                created_at=datetime.now(UTC),
            )
            await uow.permissions.create(perm)
        yield uow

    return factory, admin_role, viewer_role


@pytest.mark.asyncio
async def test_assign_permission_denied() -> None:
    """AssignPermissionUseCase raises PermissionDenied when actor has no admin."""
    from unittest.mock import AsyncMock

    coll_id = uuid4()
    factory, _, _ = _assign_permission_uow_factory(coll_id)
    perm_checker = AsyncMock()
    perm_checker.check.return_value = False

    use_case = AssignPermissionUseCase(
        unit_of_work_factory=factory,
        permission_checker=perm_checker,
    )

    with pytest.raises(PermissionDenied, match="admin"):
        await use_case.execute("actor", coll_id, "user-2", "viewer")


@pytest.mark.asyncio
async def test_assign_permission_role_not_found(
    mock_permission_checker,
) -> None:
    """AssignPermissionUseCase raises NotFound when role does not exist."""
    coll_id = uuid4()
    factory, _, _ = _assign_permission_uow_factory(coll_id)

    use_case = AssignPermissionUseCase(
        unit_of_work_factory=factory,
        permission_checker=mock_permission_checker,
    )

    with pytest.raises(NotFound, match="Role"):
        await use_case.execute("actor", coll_id, "user-2", "nonexistent")


@pytest.mark.asyncio
async def test_assign_permission_success(
    mock_permission_checker,
) -> None:
    """AssignPermissionUseCase creates new permission."""
    coll_id = uuid4()
    factory, _, viewer_role = _assign_permission_uow_factory(coll_id)

    use_case = AssignPermissionUseCase(
        unit_of_work_factory=factory,
        permission_checker=mock_permission_checker,
    )

    result = await use_case.execute("actor", coll_id, "user-2", "viewer")

    assert result.collection_id == coll_id
    assert result.subject == "user-2"
    assert result.role_id == viewer_role.id


@pytest.mark.asyncio
async def test_assign_permission_update_existing(
    mock_permission_checker,
) -> None:
    """AssignPermissionUseCase updates existing permission."""
    coll_id = uuid4()
    factory, _, viewer_role = _assign_permission_uow_factory(
        coll_id, has_existing=True
    )

    use_case = AssignPermissionUseCase(
        unit_of_work_factory=factory,
        permission_checker=mock_permission_checker,
    )

    result = await use_case.execute("actor", coll_id, "user-2", "admin")

    assert result.subject == "user-2"


# --- RevokePermissionUseCase ---


def _revoke_permission_uow_factory(collection_id, has_permission=True):
    """Build UoW for RevokePermissionUseCase."""
    @asynccontextmanager
    async def factory():
        uow = FakeUnitOfWork()
        if has_permission:
            perm = Permission(
                id=uuid4(),
                collection_id=collection_id,
                subject="user-2",
                role_id=uuid4(),
                created_at=datetime.now(UTC),
            )
            await uow.permissions.create(perm)
        yield uow

    return factory


@pytest.mark.asyncio
async def test_revoke_permission_denied() -> None:
    """RevokePermissionUseCase raises PermissionDenied when actor has no admin."""
    from unittest.mock import AsyncMock

    coll_id = uuid4()
    factory = _revoke_permission_uow_factory(coll_id)
    perm_checker = AsyncMock()
    perm_checker.check.return_value = False

    use_case = RevokePermissionUseCase(
        unit_of_work_factory=factory,
        permission_checker=perm_checker,
    )

    with pytest.raises(PermissionDenied, match="admin"):
        await use_case.execute("actor", coll_id, "user-2")


@pytest.mark.asyncio
async def test_revoke_permission_not_found(
    mock_permission_checker,
) -> None:
    """RevokePermissionUseCase raises NotFound when permission does not exist."""
    coll_id = uuid4()
    factory = _revoke_permission_uow_factory(coll_id, has_permission=False)

    use_case = RevokePermissionUseCase(
        unit_of_work_factory=factory,
        permission_checker=mock_permission_checker,
    )

    with pytest.raises(NotFound, match="Permission"):
        await use_case.execute("actor", coll_id, "user-2")


@pytest.mark.asyncio
async def test_revoke_permission_success(
    mock_permission_checker,
) -> None:
    """RevokePermissionUseCase deletes permission."""
    coll_id = uuid4()
    factory = _revoke_permission_uow_factory(coll_id)

    use_case = RevokePermissionUseCase(
        unit_of_work_factory=factory,
        permission_checker=mock_permission_checker,
    )

    await use_case.execute("actor", coll_id, "user-2")

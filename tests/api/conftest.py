"""Fixtures for API tests."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

import falcon.asgi
import pytest

from relrag.application.use_cases.collection.create_collection import CreateCollectionUseCase
from relrag.application.use_cases.collection.migrate_collection import MigrateCollectionUseCase
from relrag.application.use_cases.document.get_document import GetDocumentUseCase
from relrag.application.use_cases.document.load_document import LoadDocumentUseCase
from relrag.application.use_cases.permission.assign_permission import AssignPermissionUseCase
from relrag.application.use_cases.permission.revoke_permission import RevokePermissionUseCase
from relrag.application.use_cases.search.hybrid_search import HybridSearchUseCase
from relrag.domain.entities import Configuration, Role
from relrag.domain.value_objects import ChunkingStrategy
from relrag.infrastructure.chunking.recursive_chunker import RecursiveChunker

from tests.conftest import FakeUnitOfWork, mock_embedding_provider, mock_permission_checker


class _TestUser:
    user_id = "test-user-1"


class AuthBypassMiddleware:
    """Middleware that sets context.user for testing."""

    async def process_request(self, req, resp):
        req.context.user = _TestUser()


@pytest.fixture
def uow_factory():
    """UoW factory with admin role - yields same UoW for all requests in a test."""

    uow = FakeUnitOfWork()
    for name, desc in [("admin", "Admin"), ("editor", "Editor"), ("viewer", "Viewer")]:
        uow.roles.add_role(Role(id=uuid4(), name=name, description=desc))

    @asynccontextmanager
    async def _factory():
        yield uow

    return _factory


@pytest.fixture
def app(uow_factory, mock_permission_checker, mock_embedding_provider):
    """Falcon ASGI app with API resources for testing."""
    create_collection = CreateCollectionUseCase(unit_of_work_factory=uow_factory)
    migrate_collection = MigrateCollectionUseCase(
        unit_of_work_factory=uow_factory,
        permission_checker=mock_permission_checker,
        chunker=RecursiveChunker(),
        embedding_provider=mock_embedding_provider,
    )
    assign_permission = AssignPermissionUseCase(
        unit_of_work_factory=uow_factory,
        permission_checker=mock_permission_checker,
    )
    revoke_permission = RevokePermissionUseCase(
        unit_of_work_factory=uow_factory,
        permission_checker=mock_permission_checker,
    )
    load_document = LoadDocumentUseCase(
        unit_of_work_factory=uow_factory,
        permission_checker=mock_permission_checker,
        chunker=RecursiveChunker(),
        embedding_provider=mock_embedding_provider,
    )
    get_document = GetDocumentUseCase(
        unit_of_work_factory=uow_factory,
        permission_checker=mock_permission_checker,
    )
    hybrid_search = HybridSearchUseCase(
        unit_of_work_factory=uow_factory,
        permission_checker=mock_permission_checker,
        embedding_provider=mock_embedding_provider,
    )

    from relrag.interfaces.api.resources.collections import (
        CollectionResource,
        CollectionsResource,
    )
    from relrag.interfaces.api.resources.configurations import ConfigurationsResource
    from relrag.interfaces.api.resources.documents import (
    DocumentResource,
    DocumentsResource,
    DocumentsStreamResource,
)
    from relrag.interfaces.api.resources.health import HealthResource
    from relrag.interfaces.api.resources.migrate import MigrateResource
    from relrag.interfaces.api.resources.models import ModelsResource
    from relrag.interfaces.api.resources.permissions import (
        PermissionRevokeResource,
        PermissionsResource,
    )
    from relrag.interfaces.api.resources.search import SearchResource

    app = falcon.asgi.App(middleware=[AuthBypassMiddleware()])
    app.add_route("/v1/health", HealthResource())
    app.add_route("/v1/configurations", ConfigurationsResource(uow_factory))
    app.add_route("/v1/models", ModelsResource())
    app.add_route("/v1/collections", CollectionsResource(create_collection, uow_factory))
    app.add_route("/v1/collections/{collection_id}", CollectionResource(uow_factory, mock_permission_checker))
    app.add_route("/v1/collections/{collection_id}/migrate", MigrateResource(migrate_collection))
    app.add_route(
        "/v1/collections/{collection_id}/permissions",
        PermissionsResource(uow_factory, mock_permission_checker, assign_permission),
    )
    app.add_route(
        "/v1/collections/{collection_id}/permissions/{subject}",
        PermissionRevokeResource(revoke_permission),
    )
    app.add_route("/v1/documents/stream", DocumentsStreamResource(load_document))
    app.add_route("/v1/documents", DocumentsResource(load_document))
    app.add_route("/v1/documents/{document_id}", DocumentResource(get_document))
    app.add_route("/v1/collections/{collection_id}/search", SearchResource(hybrid_search))
    return app


@pytest.fixture
def client(app):
    """Falcon ASGI test client."""
    from falcon.testing import TestClient
    return TestClient(app)

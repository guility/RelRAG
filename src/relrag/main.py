"""Application entry point and composition root."""

import sys

import falcon.asgi

from relrag import __version__
from relrag.application.use_cases.collection.create_collection import CreateCollectionUseCase
from relrag.application.use_cases.document.get_document import GetDocumentUseCase
from relrag.application.use_cases.document.load_document import LoadDocumentUseCase
from relrag.application.use_cases.search.hybrid_search import HybridSearchUseCase
from relrag.config import get_settings
from relrag.infrastructure.auth.keycloak_provider import KeycloakProvider
from relrag.infrastructure.chunking.recursive_chunker import RecursiveChunker
from relrag.infrastructure.embedding.openai_provider import OpenAIEmbeddingProvider
from relrag.infrastructure.permission.permission_checker import RelRAGPermissionChecker
from relrag.infrastructure.persistence.postgres.connection import create_pool
from relrag.infrastructure.persistence.postgres.unit_of_work import (
    create_uow_factory,
)
from relrag.interfaces.api.middleware.auth import AuthMiddleware
from relrag.interfaces.api.middleware.pool_lifespan import PoolLifespanMiddleware
from relrag.interfaces.api.resources.collections import CollectionResource, CollectionsResource
from relrag.interfaces.api.resources.configurations import ConfigurationsResource
from relrag.interfaces.api.resources.documents import DocumentResource, DocumentsResource
from relrag.interfaces.api.resources.health import HealthResource
from relrag.interfaces.api.resources.search import SearchResource


def main() -> None:
    """CLI entry point."""
    print(f"RelRAG v{__version__}")


def create_relrag_app():
    """Composition root - build Falcon app with all dependencies."""
    settings = get_settings()
    pool = create_pool(settings.database_url)
    uow_factory = create_uow_factory(pool)

    keycloak = (
        KeycloakProvider(
            server_url=settings.keycloak_url,
            realm=settings.keycloak_realm,
            client_id=settings.keycloak_client_id,
            client_secret=settings.keycloak_client_secret,
        )
        if settings.keycloak_client_secret
        else None
    )

    permission_checker = RelRAGPermissionChecker(uow_factory)
    embedding_provider = OpenAIEmbeddingProvider(
        base_url=settings.embedding_api_url,
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
    )
    chunker = RecursiveChunker()

    load_document = LoadDocumentUseCase(
        unit_of_work_factory=uow_factory,
        permission_checker=permission_checker,
        chunker=chunker,
        embedding_provider=embedding_provider,
    )
    get_document = GetDocumentUseCase(
        unit_of_work_factory=uow_factory,
        permission_checker=permission_checker,
    )
    create_collection = CreateCollectionUseCase(
        unit_of_work_factory=uow_factory,
    )
    hybrid_search = HybridSearchUseCase(
        unit_of_work_factory=uow_factory,
        permission_checker=permission_checker,
        embedding_provider=embedding_provider,
    )

    documents_resource = DocumentsResource(load_document)
    document_resource = DocumentResource(get_document)
    collections_resource = CollectionsResource(create_collection)
    collection_resource = CollectionResource()
    configurations_resource = ConfigurationsResource(uow_factory)
    search_resource = SearchResource(hybrid_search)
    health_resource = HealthResource()

    app = falcon.asgi.App(
        middleware=[PoolLifespanMiddleware(pool), AuthMiddleware(keycloak)],
    )

    async def log_exception(req, resp, ex, params):
        import traceback
        traceback.print_exception(type(ex), ex, ex.__traceback__, file=sys.stderr)
        resp.status = falcon.HTTP_500
        resp.media = {"title": "500 Internal Server Error"}

    app.add_error_handler(Exception, log_exception)
    app.add_route("/v1/health", health_resource)
    app.add_route("/v1/health/ready", health_resource, suffix="ready")
    app.add_route("/v1/documents", documents_resource)
    app.add_route("/v1/documents/{document_id}", document_resource)
    app.add_route("/v1/collections", collections_resource)
    app.add_route("/v1/collections/{collection_id}", collection_resource)
    app.add_route("/v1/configurations", configurations_resource)
    app.add_route("/v1/collections/{collection_id}/search", search_resource)

    return app


async def run_server() -> None:
    """Run uvicorn server."""
    import uvicorn

    app = create_relrag_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)

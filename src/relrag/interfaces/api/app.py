"""Falcon ASGI application."""

import falcon.asgi
from falcon.asgi import App

from relrag.interfaces.api.resources.collections import CollectionResource, CollectionsResource
from relrag.interfaces.api.resources.configurations import ConfigurationsResource
from relrag.interfaces.api.resources.documents import DocumentResource, DocumentsResource
from relrag.interfaces.api.resources.health import HealthResource
from relrag.interfaces.api.resources.search import SearchResource


def create_app(
    documents_resource: DocumentsResource,
    document_resource: DocumentResource,
    collections_resource: CollectionsResource,
    collection_resource: CollectionResource,
    configurations_resource: ConfigurationsResource,
    search_resource: SearchResource,
    health_resource: HealthResource,
) -> App:
    """Create Falcon ASGI app with routes."""
    app = falcon.asgi.App()
    app.add_route("/v1/health", health_resource)
    app.add_route("/v1/health/ready", health_resource, suffix="ready")
    app.add_route("/v1/documents", documents_resource)
    app.add_route("/v1/documents/{document_id}", document_resource)
    app.add_route("/v1/collections", collections_resource)
    app.add_route("/v1/collections/{collection_id}", collection_resource)
    app.add_route("/v1/configurations", configurations_resource)
    app.add_route("/v1/collections/{collection_id}/search", search_resource)
    return app

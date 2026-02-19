"""Collection API resources."""

from uuid import UUID

import falcon.asgi

from relrag.application.use_cases.collection.create_collection import CreateCollectionUseCase
from relrag.domain.exceptions import NotFound


class CollectionsResource:
    """POST /v1/collections - create collection."""

    def __init__(self, create_collection: CreateCollectionUseCase) -> None:
        self._create_collection = create_collection

    async def on_post(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        """Create collection with configuration."""
        user = getattr(req.context, "user", None)
        if not user:
            resp.status = falcon.HTTP_401
            resp.media = {"error": "Unauthorized"}
            return

        try:
            body = await req.get_media()
            configuration_id = UUID(body["configuration_id"])
        except (KeyError, ValueError) as e:
            resp.status = falcon.HTTP_400
            resp.media = {"error": str(e)}
            return

        try:
            result = await self._create_collection.execute(user.user_id, configuration_id)
            resp.media = {
                "id": str(result.id),
                "configuration_id": str(result.configuration_id),
                "created_at": result.created_at.isoformat(),
                "updated_at": result.updated_at.isoformat(),
            }
            resp.status = falcon.HTTP_201
        except NotFound as e:
            resp.status = falcon.HTTP_404
            resp.media = {"error": str(e)}


class CollectionResource:
    """GET /v1/collections/{id} - get collection."""

    async def on_get(
        self,
        req: falcon.asgi.Request,
        resp: falcon.asgi.Response,
        collection_id: str,
    ) -> None:
        """Get collection by id."""
        resp.status = falcon.HTTP_501
        resp.media = {"error": "Not implemented"}

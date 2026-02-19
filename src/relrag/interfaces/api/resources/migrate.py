"""Migrate collection API resource."""

from uuid import UUID

import falcon.asgi

from relrag.application.use_cases.collection.migrate_collection import MigrateCollectionUseCase
from relrag.domain.exceptions import NotFound, PermissionDenied


class MigrateResource:
    """POST /v1/collections/{id}/migrate - migrate collection to new configuration."""

    def __init__(self, migrate_collection: MigrateCollectionUseCase) -> None:
        self._migrate = migrate_collection

    async def on_post(
        self,
        req: falcon.asgi.Request,
        resp: falcon.asgi.Response,
        collection_id: str,
    ) -> None:
        """Migrate collection to new configuration."""
        user = getattr(req.context, "user", None)
        if not user:
            resp.status = falcon.HTTP_401
            resp.media = {"error": "Unauthorized"}
            return

        try:
            coll_id = UUID(collection_id)
        except ValueError:
            resp.status = falcon.HTTP_400
            resp.media = {"error": "Invalid collection ID"}
            return

        try:
            body = await req.get_media()
            new_config_id = UUID(body["new_configuration_id"])
        except (KeyError, ValueError) as e:
            resp.status = falcon.HTTP_400
            resp.media = {"error": str(e)}
            return

        try:
            migrated = await self._migrate.execute(user.user_id, coll_id, new_config_id)
            resp.media = {"migrated": migrated}
            resp.status = falcon.HTTP_200
        except PermissionDenied:
            resp.status = falcon.HTTP_403
            resp.media = {"error": "Permission denied"}
        except NotFound as e:
            resp.status = falcon.HTTP_404
            resp.media = {"error": str(e)}

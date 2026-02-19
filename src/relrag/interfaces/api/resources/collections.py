"""Collection API resources."""

from uuid import UUID

import falcon.asgi

from relrag.application.use_cases.collection.create_collection import CreateCollectionUseCase
from relrag.domain.exceptions import NotFound
from relrag.domain.value_objects import PermissionAction


class CollectionsResource:
    """GET/POST /v1/collections - list and create collections."""

    def __init__(self, create_collection: CreateCollectionUseCase, unit_of_work_factory: type) -> None:
        self._create_collection = create_collection
        self._uow_factory = unit_of_work_factory

    async def on_get(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        """List collections where user has permission."""
        user = getattr(req.context, "user", None)
        if not user:
            resp.status = falcon.HTTP_401
            resp.media = {"error": "Unauthorized"}
            return

        cursor = req.get_param("cursor")
        limit = req.get_param_as_int("limit") or 20
        limit = min(max(limit, 1), 100)

        async with self._uow_factory() as uow:
            colls, next_cursor = await uow.collections.list_by_subject(
                user.user_id,
                cursor=cursor,
                limit=limit,
            )

        resp.media = {
            "items": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "configuration_id": str(c.configuration_id),
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                }
                for c in colls
            ],
            "next_cursor": next_cursor,
        }
        resp.status = falcon.HTTP_200

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
            name = (body.get("name") or "").strip() or None
        except (KeyError, ValueError) as e:
            resp.status = falcon.HTTP_400
            resp.media = {"error": str(e)}
            return

        try:
            result = await self._create_collection.execute(
                user.user_id, configuration_id, name=name
            )
            resp.media = {
                "id": str(result.id),
                "name": result.name,
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

    def __init__(self, unit_of_work_factory: type, permission_checker) -> None:
        self._uow_factory = unit_of_work_factory
        self._permission_checker = permission_checker

    async def on_get(
        self,
        req: falcon.asgi.Request,
        resp: falcon.asgi.Response,
        collection_id: str,
    ) -> None:
        """Get collection by id."""
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

        has_read = await self._permission_checker.check(
            user.user_id, coll_id, PermissionAction.READ
        )
        if not has_read:
            resp.status = falcon.HTTP_403
            resp.media = {"error": "Permission denied"}
            return

        async with self._uow_factory() as uow:
            coll = await uow.collections.get_by_id(coll_id)
            if not coll:
                resp.status = falcon.HTTP_404
                resp.media = {"error": "Collection not found"}
                return

        resp.media = {
            "id": str(coll.id),
            "name": coll.name,
            "configuration_id": str(coll.configuration_id),
            "created_at": coll.created_at.isoformat(),
            "updated_at": coll.updated_at.isoformat(),
        }
        resp.status = falcon.HTTP_200

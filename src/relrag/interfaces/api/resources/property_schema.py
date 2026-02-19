"""Property schema API - list property keys and values for filter UI."""

from uuid import UUID

import falcon.asgi

from relrag.domain.value_objects import PermissionAction

# Human-readable labels for property keys (filter UI).
PROPERTY_KEY_LABELS: dict[str, str] = {
    "title": "Название",
    "author": "Автор",
    "created_date": "Дата создания",
    "modified_date": "Дата изменения",
    "page_count": "Кол-во страниц",
    "language": "Язык",
    "source_file_name": "Имя файла",
    "source_file_type": "Тип файла",
}


class PropertySchemaResource:
    """GET /v1/collections/{collection_id}/property-schema."""

    def __init__(self, unit_of_work_factory: type, permission_checker) -> None:
        self._uow_factory = unit_of_work_factory
        self._permission_checker = permission_checker

    async def on_get(
        self,
        req: falcon.asgi.Request,
        resp: falcon.asgi.Response,
        collection_id: str,
    ) -> None:
        """Return property keys, types and distinct values for the collection."""
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
            schema = await uow.properties.list_schema_by_collection(coll_id)
        resp.media = {
            "properties": [
                {
                    "key": item.key,
                    "label": PROPERTY_KEY_LABELS.get(item.key, item.key),
                    "type": item.property_type.value,
                    "values": item.values,
                }
                for item in schema
            ],
        }
        resp.status = falcon.HTTP_200

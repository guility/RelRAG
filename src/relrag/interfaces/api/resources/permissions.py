"""Permissions API resources."""

from uuid import UUID

import falcon.asgi

from relrag.application.use_cases.permission.assign_permission import AssignPermissionUseCase
from relrag.application.use_cases.permission.revoke_permission import RevokePermissionUseCase
from relrag.domain.exceptions import NotFound, PermissionDenied


class PermissionsResource:
    """GET/POST /v1/collections/{id}/permissions - list and assign permissions."""

    def __init__(
        self,
        unit_of_work_factory: type,
        permission_checker,
        assign_permission: AssignPermissionUseCase,
    ) -> None:
        self._uow_factory = unit_of_work_factory
        self._permission_checker = permission_checker
        self._assign = assign_permission

    async def on_get(
        self,
        req: falcon.asgi.Request,
        resp: falcon.asgi.Response,
        collection_id: str,
    ) -> None:
        """List permissions for collection."""
        user = getattr(req.context, "user", None)
        if not user:
            resp.status = falcon.HTTP_401
            resp.media = {"error": "Unauthorized"}
            return

        from relrag.domain.value_objects import PermissionAction

        has_admin = await self._permission_checker.check(
            user.user_id, UUID(collection_id), PermissionAction.ADMIN
        )
        if not has_admin:
            resp.status = falcon.HTTP_403
            resp.media = {"error": "Permission denied"}
            return

        async with self._uow_factory() as uow:
            perms = await uow.permissions.list_by_collection(UUID(collection_id))
            items = []
            for p in perms:
                role = await uow.roles.get_by_id(p.role_id)
                role_name = role.name if role else "unknown"
                items.append({
                    "id": str(p.id),
                    "subject": p.subject,
                    "role": role_name,
                    "actions_override": p.actions_override,
                })

        resp.media = {"items": items}
        resp.status = falcon.HTTP_200

    async def on_post(
        self,
        req: falcon.asgi.Request,
        resp: falcon.asgi.Response,
        collection_id: str,
    ) -> None:
        """Assign permission to subject on collection."""
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
            subject = body["subject"]
            role = body.get("role", "viewer")
        except KeyError as e:
            resp.status = falcon.HTTP_400
            resp.media = {"error": f"Missing required field: {e}"}
            return

        try:
            perm = await self._assign.execute(
                user.user_id, coll_id, subject, role
            )
            role_obj = None
            async with self._uow_factory() as uow:
                role_obj = await uow.roles.get_by_id(perm.role_id)
            resp.media = {
                "id": str(perm.id),
                "subject": perm.subject,
                "role": role_obj.name if role_obj else role,
            }
            resp.status = falcon.HTTP_201
        except PermissionDenied:
            resp.status = falcon.HTTP_403
            resp.media = {"error": "Permission denied"}
        except NotFound as e:
            resp.status = falcon.HTTP_404
            resp.media = {"error": str(e)}


class PermissionRevokeResource:
    """DELETE /v1/collections/{id}/permissions/{subject} - revoke permission."""

    def __init__(self, revoke_permission: RevokePermissionUseCase) -> None:
        self._revoke = revoke_permission

    async def on_delete(
        self,
        req: falcon.asgi.Request,
        resp: falcon.asgi.Response,
        collection_id: str,
        subject: str,
    ) -> None:
        """Revoke permission for subject on collection."""
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
            await self._revoke.execute(user.user_id, coll_id, subject)
            resp.status = falcon.HTTP_204
        except PermissionDenied:
            resp.status = falcon.HTTP_403
            resp.media = {"error": "Permission denied"}
        except NotFound:
            resp.status = falcon.HTTP_404
            resp.media = {"error": "Permission not found"}

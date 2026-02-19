"""Revoke permission use case."""

from uuid import UUID

from relrag.application.ports import PermissionChecker
from relrag.domain.exceptions import NotFound, PermissionDenied
from relrag.domain.value_objects import PermissionAction


class RevokePermissionUseCase:
    """Revoke permission (remove role) from user on collection."""

    def __init__(
        self,
        unit_of_work_factory: type,
        permission_checker: PermissionChecker,
    ) -> None:
        self._uow_factory = unit_of_work_factory
        self._permission_checker = permission_checker

    async def execute(
        self,
        actor_id: str,
        collection_id: UUID,
        subject: str,
    ) -> None:
        """Revoke permission for subject on collection. Actor must have admin."""
        has_admin = await self._permission_checker.check(
            actor_id, collection_id, PermissionAction.ADMIN
        )
        if not has_admin:
            raise PermissionDenied("User does not have admin access to collection")

        async with self._uow_factory() as uow:
            perm = await uow.permissions.get_for_collection(collection_id, subject)
            if not perm:
                raise NotFound("Permission", f"{collection_id}/{subject}")
            await uow.permissions.delete(perm.id)

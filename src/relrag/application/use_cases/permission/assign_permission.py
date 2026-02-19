"""Assign permission use case."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from relrag.application.ports import PermissionChecker
from relrag.domain.entities import Permission
from relrag.domain.exceptions import NotFound, PermissionDenied
from relrag.domain.value_objects import PermissionAction


class AssignPermissionUseCase:
    """Assign permission (role) to user on collection."""

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
        role_name: str,
        actions_override: list[str] | None = None,
    ) -> Permission:
        """Assign role to subject on collection. Actor must have admin on collection."""
        has_admin = await self._permission_checker.check(
            actor_id, collection_id, PermissionAction.ADMIN
        )
        if not has_admin:
            raise PermissionDenied("User does not have admin access to collection")

        async with self._uow_factory() as uow:
            role = await uow.roles.get_by_name(role_name)
            if not role:
                raise NotFound("Role", role_name)

            existing = await uow.permissions.get_for_collection(collection_id, subject)
            now = datetime.now(UTC)
            if existing:
                existing.actions_override = actions_override
                existing.role_id = role.id
                await uow.permissions.update(existing)
                return existing

            permission = Permission(
                id=uuid4(),
                collection_id=collection_id,
                subject=subject,
                role_id=role.id,
                actions_override=actions_override,
                created_at=now,
            )
            await uow.permissions.create(permission)
            return permission

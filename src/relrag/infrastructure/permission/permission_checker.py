"""Permission checker implementation - checks against Permission table."""

from uuid import UUID

from relrag.domain.value_objects import PermissionAction


class RelRAGPermissionChecker:
    """Checks user permissions against Permission table and role actions."""

    def __init__(self, unit_of_work_factory: type) -> None:
        self._uow_factory = unit_of_work_factory

    async def check(self, user_id: str, collection_id: UUID, action: PermissionAction) -> bool:
        """Check if user has action on collection."""
        async with self._uow_factory() as uow:
            perm = await uow.permissions.get_for_collection(collection_id, user_id)
            if not perm:
                return False

            actions = perm.actions_override
            if actions is None:
                role_actions = await uow.roles.get_actions_for_role(perm.role_id)
                actions = role_actions

            return action.value in actions

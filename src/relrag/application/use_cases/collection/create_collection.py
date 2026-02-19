"""Create collection use case."""

from datetime import UTC
from uuid import UUID, uuid4

from relrag.domain.entities import Collection, Permission
from relrag.domain.exceptions import NotFound


class CreateCollectionUseCase:
    """Create collection with configuration and assign admin to creator."""

    def __init__(self, unit_of_work_factory: type) -> None:
        self._uow_factory = unit_of_work_factory

    async def execute(
        self,
        user_id: str,
        configuration_id: UUID,
        name: str | None = None,
    ) -> Collection:
        """Create collection and assign admin role to creator."""
        async with self._uow_factory() as uow:
            config = await uow.configurations.get_by_id(configuration_id)
            if not config:
                raise NotFound("Configuration", str(configuration_id))

            from datetime import datetime

            now = datetime.now(UTC)
            coll_id = uuid4()
            collection = Collection(
                id=coll_id,
                configuration_id=configuration_id,
                created_at=now,
                updated_at=now,
                deleted_at=None,
                name=name or None,
            )
            await uow.collections.create(collection)

            admin_role = await uow.roles.get_by_name("admin")
            if not admin_role:
                raise NotFound("Role", "admin")

            permission = Permission(
                id=uuid4(),
                collection_id=coll_id,
                subject=user_id,
                role_id=admin_role.id,
                actions_override=None,
                created_at=now,
            )
            await uow.permissions.create(permission)

        return collection

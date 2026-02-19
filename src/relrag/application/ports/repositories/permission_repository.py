"""Permission repository port."""

from typing import Protocol
from uuid import UUID

from relrag.domain.entities import Permission


class PermissionRepository(Protocol):
    """Port for permission persistence."""

    async def get_by_id(self, permission_id: UUID) -> Permission | None: ...

    async def list_by_collection(self, collection_id: UUID) -> list[Permission]: ...

    async def list_by_subject(self, subject: str) -> list[Permission]: ...

    async def get_for_collection(self, collection_id: UUID, subject: str) -> Permission | None: ...

    async def create(self, permission: Permission) -> Permission: ...

    async def update(self, permission: Permission) -> None: ...

    async def delete(self, permission_id: UUID) -> None: ...

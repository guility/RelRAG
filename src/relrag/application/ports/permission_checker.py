"""Permission checker port - RBAC authorization."""

from typing import Protocol
from uuid import UUID

from relrag.domain.value_objects import PermissionAction


class PermissionChecker(Protocol):
    """Port for checking user permissions on collections."""

    async def check(self, user_id: str, collection_id: UUID, action: PermissionAction) -> bool: ...

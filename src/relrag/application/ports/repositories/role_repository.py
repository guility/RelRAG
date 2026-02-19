"""Role repository port."""

from typing import Protocol
from uuid import UUID

from relrag.domain.entities import Role


class RoleRepository(Protocol):
    """Port for role persistence."""

    async def get_by_id(self, role_id: UUID) -> Role | None: ...

    async def get_by_name(self, name: str) -> Role | None: ...

    async def list_all(self) -> list[Role]: ...

    async def get_actions_for_role(self, role_id: UUID) -> list[str]: ...

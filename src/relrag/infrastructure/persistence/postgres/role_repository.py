"""PostgreSQL role repository implementation."""

from uuid import UUID

from psycopg import AsyncConnection

from relrag.domain.entities import Role


class PostgresRoleRepository:
    """Role repository implementation."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def get_by_id(self, role_id: UUID) -> Role | None:
        """Get role by id."""
        cur = await self._conn.execute(
            "SELECT id, name, description FROM role WHERE id = %s",
            (role_id,),
        )
        r = await cur.fetchone()
        if not r:
            return None
        return Role(id=r[0], name=r[1], description=r[2])

    async def get_by_name(self, name: str) -> Role | None:
        """Get role by name."""
        cur = await self._conn.execute(
            "SELECT id, name, description FROM role WHERE name = %s",
            (name,),
        )
        r = await cur.fetchone()
        if not r:
            return None
        return Role(id=r[0], name=r[1], description=r[2])

    async def list_all(self) -> list[Role]:
        """List all roles."""
        cur = await self._conn.execute("SELECT id, name, description FROM role")
        rows = await cur.fetchall()
        return [Role(id=r[0], name=r[1], description=r[2]) for r in rows]

    async def get_actions_for_role(self, role_id: UUID) -> list[str]:
        """Get actions for role."""
        cur = await self._conn.execute(
            "SELECT action FROM role_permission WHERE role_id = %s",
            (role_id,),
        )
        rows = await cur.fetchall()
        return [r[0] for r in rows]

"""PostgreSQL permission repository implementation."""

from uuid import UUID

from psycopg import AsyncConnection

from relrag.domain.entities import Permission


class PostgresPermissionRepository:
    """Permission repository implementation."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def get_by_id(self, permission_id: UUID) -> Permission | None:
        """Get permission by id."""
        cur = await self._conn.execute(
            "SELECT id, collection_id, subject, role_id, actions_override, created_at, created_by "
            "FROM permission WHERE id = %s",
            (permission_id,),
        )
        r = await cur.fetchone()
        if not r:
            return None
        return Permission(
            id=r[0],
            collection_id=r[1],
            subject=r[2],
            role_id=r[3],
            actions_override=r[4],
            created_at=r[5],
            created_by=r[6],
        )

    async def list_by_collection(self, collection_id: UUID) -> list[Permission]:
        """List permissions for collection."""
        cur = await self._conn.execute(
            "SELECT id, collection_id, subject, role_id, actions_override, created_at, created_by "
            "FROM permission WHERE collection_id = %s",
            (collection_id,),
        )
        rows = await cur.fetchall()
        return [
            Permission(
                id=r[0],
                collection_id=r[1],
                subject=r[2],
                role_id=r[3],
                actions_override=r[4],
                created_at=r[5],
                created_by=r[6],
            )
            for r in rows
        ]

    async def list_by_subject(self, subject: str) -> list[Permission]:
        """List permissions for subject."""
        cur = await self._conn.execute(
            "SELECT id, collection_id, subject, role_id, actions_override, created_at, created_by "
            "FROM permission WHERE subject = %s",
            (subject,),
        )
        rows = await cur.fetchall()
        return [
            Permission(
                id=r[0],
                collection_id=r[1],
                subject=r[2],
                role_id=r[3],
                actions_override=r[4],
                created_at=r[5],
                created_by=r[6],
            )
            for r in rows
        ]

    async def get_for_collection(self, collection_id: UUID, subject: str) -> Permission | None:
        """Get permission for subject on collection."""
        cur = await self._conn.execute(
            "SELECT id, collection_id, subject, role_id, actions_override, created_at, created_by "
            "FROM permission WHERE collection_id = %s AND subject = %s",
            (collection_id, subject),
        )
        r = await cur.fetchone()
        if not r:
            return None
        return Permission(
            id=r[0],
            collection_id=r[1],
            subject=r[2],
            role_id=r[3],
            actions_override=r[4],
            created_at=r[5],
            created_by=r[6],
        )

    async def create(self, permission: Permission) -> Permission:
        """Create permission."""
        await self._conn.execute(
            "INSERT INTO permission (id, collection_id, subject, role_id, actions_override, created_at, created_by) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                permission.id,
                permission.collection_id,
                permission.subject,
                permission.role_id,
                permission.actions_override,
                permission.created_at,
                permission.created_by,
            ),
        )
        return permission

    async def update(self, permission: Permission) -> None:
        """Update permission."""
        await self._conn.execute(
            "UPDATE permission SET role_id=%s, actions_override=%s WHERE id=%s",
            (permission.role_id, permission.actions_override, permission.id),
        )

    async def delete(self, permission_id: UUID) -> None:
        """Delete permission."""
        await self._conn.execute(
            "DELETE FROM permission WHERE id = %s",
            (permission_id,),
        )

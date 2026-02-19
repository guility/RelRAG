"""PostgreSQL Unit of Work implementation."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg_pool import AsyncConnectionPool

from relrag.infrastructure.persistence.postgres.chunk_repository import (
    PostgresChunkRepository,
)
from relrag.infrastructure.persistence.postgres.collection_repository import (
    PostgresCollectionRepository,
)
from relrag.infrastructure.persistence.postgres.configuration_repository import (
    PostgresConfigurationRepository,
)
from relrag.infrastructure.persistence.postgres.document_repository import (
    PostgresDocumentRepository,
)
from relrag.infrastructure.persistence.postgres.pack_repository import (
    PostgresPackRepository,
)
from relrag.infrastructure.persistence.postgres.permission_repository import (
    PostgresPermissionRepository,
)
from relrag.infrastructure.persistence.postgres.property_repository import (
    PostgresPropertyRepository,
)
from relrag.infrastructure.persistence.postgres.role_repository import (
    PostgresRoleRepository,
)


class PostgresUnitOfWork:
    """PostgreSQL Unit of Work - one connection, one transaction."""

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool
        self._conn: object | None = None
        self._conn_cm: object | None = None

    async def __aenter__(self) -> "PostgresUnitOfWork":
        self._conn_cm = self._pool.connection()
        self._conn = await self._conn_cm.__aenter__()
        self._documents = PostgresDocumentRepository(self._conn)
        self._packs = PostgresPackRepository(self._conn)
        self._chunks = PostgresChunkRepository(self._conn)
        self._collections = PostgresCollectionRepository(self._conn)
        self._configurations = PostgresConfigurationRepository(self._conn)
        self._properties = PostgresPropertyRepository(self._conn)
        self._permissions = PostgresPermissionRepository(self._conn)
        self._roles = PostgresRoleRepository(self._conn)
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if exc_type and self._conn:
            await self._conn.rollback()
        if self._conn_cm:
            await self._conn_cm.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def documents(self) -> PostgresDocumentRepository:
        return self._documents

    @property
    def packs(self) -> PostgresPackRepository:
        return self._packs

    @property
    def chunks(self) -> PostgresChunkRepository:
        return self._chunks

    @property
    def collections(self) -> PostgresCollectionRepository:
        return self._collections

    @property
    def configurations(self) -> PostgresConfigurationRepository:
        return self._configurations

    @property
    def properties(self) -> PostgresPropertyRepository:
        return self._properties

    @property
    def permissions(self) -> PostgresPermissionRepository:
        return self._permissions

    @property
    def roles(self) -> PostgresRoleRepository:
        return self._roles

    async def commit(self) -> None:
        if self._conn:
            await self._conn.commit()

    async def rollback(self) -> None:
        if self._conn:
            await self._conn.rollback()


def create_uow_factory(pool: AsyncConnectionPool) -> object:
    """Create UnitOfWork factory (async context manager)."""

    @asynccontextmanager
    async def factory() -> AsyncIterator[PostgresUnitOfWork]:
        uow = PostgresUnitOfWork(pool)
        async with uow:
            try:
                yield uow
                await uow.commit()
            except BaseException:
                await uow.rollback()
                raise

    return factory

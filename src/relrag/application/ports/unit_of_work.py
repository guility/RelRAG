"""Unit of Work port - transactional boundary."""

from collections.abc import AsyncIterator
from typing import Protocol

from relrag.application.ports.repositories.chunk_repository import ChunkRepository
from relrag.application.ports.repositories.collection_repository import (
    CollectionRepository,
)
from relrag.application.ports.repositories.configuration_repository import (
    ConfigurationRepository,
)
from relrag.application.ports.repositories.document_repository import DocumentRepository
from relrag.application.ports.repositories.pack_repository import PackRepository
from relrag.application.ports.repositories.permission_repository import (
    PermissionRepository,
)
from relrag.application.ports.repositories.property_repository import (
    PropertyRepository,
)
from relrag.application.ports.repositories.role_repository import RoleRepository


class UnitOfWork(Protocol):
    """Unit of Work - manages transaction and repository access."""

    @property
    def documents(self) -> DocumentRepository: ...

    @property
    def packs(self) -> PackRepository: ...

    @property
    def chunks(self) -> ChunkRepository: ...

    @property
    def collections(self) -> CollectionRepository: ...

    @property
    def properties(self) -> PropertyRepository: ...

    @property
    def configurations(self) -> ConfigurationRepository: ...

    @property
    def permissions(self) -> PermissionRepository: ...

    @property
    def roles(self) -> RoleRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class UnitOfWorkFactory(Protocol):
    """Factory for creating UnitOfWork instances."""

    async def __call__(self) -> AsyncIterator[UnitOfWork]: ...

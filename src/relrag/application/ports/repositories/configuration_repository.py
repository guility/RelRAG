"""Configuration repository port."""

from typing import Protocol
from uuid import UUID

from relrag.domain.entities import Configuration


class ConfigurationRepository(Protocol):
    """Port for configuration persistence."""

    async def get_by_id(self, configuration_id: UUID) -> Configuration | None: ...

    async def get_by_collection_id(self, collection_id: UUID) -> Configuration | None: ...

    async def create(self, configuration: Configuration) -> Configuration: ...

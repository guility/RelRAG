"""Collection entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Collection:
    """Collection - groups packs with a configuration."""

    id: UUID
    configuration_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

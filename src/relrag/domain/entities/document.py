"""Document entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Document:
    """Document with source content and hash for deduplication."""

    id: UUID
    content: str
    source_hash: bytes
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

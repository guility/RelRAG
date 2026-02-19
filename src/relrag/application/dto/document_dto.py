"""Document DTOs."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class DocumentCreateInput:
    """Input for creating a document."""

    collection_id: UUID
    content: str
    properties: dict[str, tuple[str, str]]  # key -> (value, type)
    source_hash: bytes | None = None


@dataclass
class DocumentOutput:
    """Output DTO for document."""

    id: UUID
    content: str
    source_hash: bytes
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

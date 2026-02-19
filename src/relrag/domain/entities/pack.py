"""Pack entity - result of splitting a document into chunks."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Pack:
    """Pack - set of chunks from a document split by a specific strategy."""

    id: UUID
    document_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

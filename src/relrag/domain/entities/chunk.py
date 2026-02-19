"""Chunk entity - text segment with embedding."""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class Chunk:
    """Chunk - text segment with vector embedding."""

    id: UUID
    pack_id: UUID
    content: str
    embedding: list[float]
    position: int

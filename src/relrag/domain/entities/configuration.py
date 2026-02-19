"""Configuration entity - chunking and embedding settings."""

from dataclasses import dataclass
from uuid import UUID

from relrag.domain.value_objects import ChunkingStrategy


@dataclass
class Configuration:
    """Configuration - chunking strategy and embedding model for a collection."""

    id: UUID
    chunking_strategy: ChunkingStrategy
    embedding_model: str
    embedding_dimensions: int
    chunk_size: int
    chunk_overlap: int

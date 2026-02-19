"""Chunking configuration DTO."""

from dataclasses import dataclass

from relrag.domain.value_objects import ChunkingStrategy


@dataclass
class ChunkingConfig:
    """Configuration for text chunking."""

    chunk_size: int
    chunk_overlap: int
    strategy: ChunkingStrategy

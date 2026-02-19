"""Chunking strategy for document splitting."""

from enum import StrEnum


class ChunkingStrategy(StrEnum):
    """Supported chunking strategies."""

    RECURSIVE = "recursive"
    FIXED = "fixed"
    SEMANTIC = "semantic"

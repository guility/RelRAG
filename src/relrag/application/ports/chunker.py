"""Chunker port - text splitting strategies."""

from typing import Protocol

from relrag.application.dto.chunking_config import ChunkingConfig


class Chunker(Protocol):
    """Port for splitting text into chunks."""

    def chunk(self, text: str, config: ChunkingConfig) -> list[str]: ...

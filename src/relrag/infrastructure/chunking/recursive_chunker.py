"""Recursive text chunker implementation."""

from relrag.application.dto.chunking_config import ChunkingConfig
from relrag.domain.value_objects import ChunkingStrategy


class RecursiveChunker:
    """Chunker using recursive character splitting."""

    def chunk(self, text: str, config: ChunkingConfig) -> list[str]:
        """Split text into chunks with overlap."""
        if config.strategy != ChunkingStrategy.RECURSIVE:
            raise ValueError(f"Unsupported strategy: {config.strategy}")

        text = text.strip()
        if not text:
            return []

        chunk_size = config.chunk_size
        chunk_overlap = config.chunk_overlap
        step = max(1, chunk_size - chunk_overlap)
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start += step
        return chunks

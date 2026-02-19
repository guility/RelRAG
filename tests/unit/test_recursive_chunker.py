"""Unit tests for RecursiveChunker."""

import pytest

from relrag.application.dto.chunking_config import ChunkingConfig
from relrag.domain.value_objects import ChunkingStrategy
from relrag.infrastructure.chunking.recursive_chunker import RecursiveChunker


def test_chunk_splits_text_with_overlap(chunking_config: ChunkingConfig) -> None:
    """Text is split into chunks with overlap."""
    chunker = RecursiveChunker()
    text = "a" * 250  # 250 chars, chunk_size=100, overlap=20, step=80
    chunks = chunker.chunk(text, chunking_config)
    assert len(chunks) >= 2
    assert all(len(c) <= 100 for c in chunks)
    # First chunk ~100 chars, second starts at position 80
    assert chunks[0] == "a" * 100
    assert chunks[1] == "a" * 80 + "a" * 20  # overlap 20 + 80 new = 100


def test_chunk_empty_text_returns_empty_list(chunking_config: ChunkingConfig) -> None:
    """Empty or whitespace-only text returns empty list."""
    chunker = RecursiveChunker()
    assert chunker.chunk("", chunking_config) == []
    assert chunker.chunk("   ", chunking_config) == []
    assert chunker.chunk("\n\t  ", chunking_config) == []


def test_chunk_unsupported_strategy_raises() -> None:
    """Unsupported chunking strategy raises ValueError."""
    chunker = RecursiveChunker()
    config = ChunkingConfig(
        chunk_size=100,
        chunk_overlap=20,
        strategy=ChunkingStrategy.FIXED,
    )
    with pytest.raises(ValueError, match="Unsupported strategy"):
        chunker.chunk("some text", config)


def test_chunk_single_chunk(chunking_config: ChunkingConfig) -> None:
    """Short text produces single chunk."""
    chunker = RecursiveChunker()
    text = "short"
    chunks = chunker.chunk(text, chunking_config)
    assert len(chunks) == 1
    assert chunks[0] == "short"


def test_chunk_overlap_ge_chunk_size() -> None:
    """When overlap >= chunk_size, step is 1 (max overlap)."""
    config = ChunkingConfig(
        chunk_size=10,
        chunk_overlap=9,
        strategy=ChunkingStrategy.RECURSIVE,
    )
    chunker = RecursiveChunker()
    text = "a" * 50
    chunks = chunker.chunk(text, config)
    assert len(chunks) >= 2
    assert all(len(c) <= 10 for c in chunks)


def test_chunk_strips_whitespace(chunking_config: ChunkingConfig) -> None:
    """Input is stripped before chunking."""
    chunker = RecursiveChunker()
    text = "  hello world  "
    chunks = chunker.chunk(text, chunking_config)
    assert len(chunks) == 1
    assert chunks[0] == "hello world"

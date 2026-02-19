"""Unit tests for SourceHash value object."""

import pytest

from relrag.domain.value_objects import SourceHash


def test_source_hash_valid() -> None:
    """SourceHash accepts 16-byte value."""
    h = SourceHash(value=b"a" * 16)
    assert h.value == b"a" * 16


def test_source_hash_invalid_length() -> None:
    """SourceHash raises ValueError for non-16-byte value."""
    with pytest.raises(ValueError, match="16 bytes"):
        SourceHash(value=b"short")
    with pytest.raises(ValueError, match="16 bytes"):
        SourceHash(value=b"x" * 20)

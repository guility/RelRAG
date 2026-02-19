"""Source document hash for deduplication."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceHash:
    """MD5 hash of source document (binary)."""

    value: bytes

    def __post_init__(self) -> None:
        if len(self.value) != 16:
            raise ValueError("MD5 hash must be 16 bytes")

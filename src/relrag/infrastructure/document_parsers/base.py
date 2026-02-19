"""Base protocol for document parsers."""

from typing import Protocol

from relrag.domain.value_objects import PropertyType


class ParseResult:
    """Result of parsing a file: extracted text and normalized properties."""

    __slots__ = ("text", "properties")

    def __init__(
        self,
        text: str,
        properties: dict[str, tuple[str, PropertyType]],
    ) -> None:
        self.text = text
        self.properties = properties


class DocumentParser(Protocol):
    """Parser that extracts text and metadata from file bytes."""

    def parse(
        self,
        data: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> ParseResult:
        """Extract text and metadata. Raises on unsupported format or parse error."""
        ...

"""Document parsers: extract text and metadata from files."""

from relrag.infrastructure.document_parsers.base import ParseResult
from relrag.infrastructure.document_parsers.registry import (
    parse_file,
    supported_extensions,
)

__all__ = ["ParseResult", "parse_file", "supported_extensions"]

"""Parser for .epub (e-book)."""

import io
import re
from html import unescape
from pathlib import Path

from ebooklib import epub
from ebooklib.epub import EpubBook

from relrag.domain.value_objects import PropertyType
from relrag.infrastructure.document_parsers.base import ParseResult
from relrag.infrastructure.document_parsers.metadata_keys import (
    normalize_value_for_storage,
)


def _get_dc(book: EpubBook, key: str) -> str | None:
    """Get first Dublin Core metadata value."""
    try:
        values = book.get_metadata("DC", key)
    except Exception:
        return None
    if not values or not values[0]:
        return None
    v = values[0][0] if isinstance(values[0], (list, tuple)) else values[0]
    return str(v) if v else None


def parse_epub(data: bytes, filename: str | None = None) -> ParseResult:
    """Extract text from chapters and metadata from .epub."""
    try:
        book = epub.read_epub(io.BytesIO(data))
    except Exception as e:
        raise ValueError(f"Invalid or corrupted epub file: {e}") from e
    parts: list[str] = []
    for item in book.get_items():
        if item.get_type() == 9:  # ITEM_DOCUMENT
            try:
                html = item.get_content().decode("utf-8", errors="replace")
            except Exception:
                continue
            text = re.sub(r"<[^>]+>", " ", html)
            text = unescape(text)
            text = " ".join(text.split())
            if text:
                parts.append(text)
    text = "\n\n".join(parts) if parts else " "
    properties: dict[str, tuple[str, PropertyType]] = {}
    for dc_key, (canon_key, ptype) in [("title", ("title", PropertyType.STRING)), ("creator", ("author", PropertyType.STRING)), ("language", ("language", PropertyType.STRING)), ("date", ("created_date", PropertyType.DATE))]:
        val = _get_dc(book, dc_key)
        if val:
            properties[canon_key] = (normalize_value_for_storage(val), ptype)
    if filename:
        p = Path(filename)
        properties["source_file_name"] = (normalize_value_for_storage(p.name), PropertyType.STRING)
        properties["source_file_type"] = (normalize_value_for_storage("epub"), PropertyType.STRING)
    return ParseResult(text=text, properties=properties)

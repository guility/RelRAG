"""Parser for PDF."""

import io
from pathlib import Path

from pypdf import PdfReader

from relrag.domain.value_objects import PropertyType
from relrag.infrastructure.document_parsers.base import ParseResult
from relrag.infrastructure.document_parsers.metadata_keys import (
    PARSER_KEY_TO_CANONICAL,
    normalize_value_for_storage,
)


def _parse_pdf_date(value: str | None) -> str:
    """Convert PDF date string (D:YYYYMMDD...) to ISO-like string."""
    if not value or not value.startswith("D:"):
        return normalize_value_for_storage(value)
    s = value[2:].strip()
    if len(s) >= 8:
        y, m, d = s[:4], s[4:6], s[6:8]
        return f"{y}-{m}-{d}"
    return value


def _map_metadata(reader: PdfReader) -> dict[str, tuple[str, PropertyType]]:
    """Map PDF metadata to canonical keys."""
    result: dict[str, tuple[str, PropertyType]] = {}
    meta = reader.metadata
    if not meta:
        return result
    raw_map: dict[str, str] = {}
    for key in ("/Title", "/Author", "/Subject", "/Creator", "/Producer", "/CreationDate", "/ModDate", "/Lang"):
        if key in meta:
            raw_map[key] = str(meta[key]) if meta[key] is not None else ""
    for parser_key, val in raw_map.items():
        if not val:
            continue
        canon = PARSER_KEY_TO_CANONICAL.get(parser_key)
        if not canon:
            continue
        canonical_key, ptype = canon
        if "Date" in parser_key:
            str_val = _parse_pdf_date(val)
        else:
            str_val = normalize_value_for_storage(val)
        result[canonical_key] = (str_val, ptype)
    return result


def parse_pdf(data: bytes, filename: str | None = None) -> ParseResult:
    """Extract text and metadata from PDF bytes."""
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as e:
        raise ValueError(f"Invalid or corrupted PDF: {e}") from e
    parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    text = "\n\n".join(parts) if parts else " "
    properties = _map_metadata(reader)
    properties["page_count"] = (str(len(reader.pages)), PropertyType.INT)
    if filename:
        p = Path(filename)
        properties["source_file_name"] = (normalize_value_for_storage(p.name), PropertyType.STRING)
        properties["source_file_type"] = (normalize_value_for_storage("pdf"), PropertyType.STRING)
    return ParseResult(text=text, properties=properties)

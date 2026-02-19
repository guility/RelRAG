"""Parser for plain text, markdown, CSV, TSV."""

import csv
import io
from pathlib import Path

from relrag.domain.value_objects import PropertyType
from relrag.infrastructure.document_parsers.base import ParseResult
from relrag.infrastructure.document_parsers.metadata_keys import (
    normalize_value_for_storage,
)


def parse_text(data: bytes, filename: str | None = None) -> ParseResult:
    """Treat as UTF-8 text. No metadata except source_file_name/type."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("cp1251")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")
    properties: dict[str, tuple[str, PropertyType]] = {}
    if filename:
        p = Path(filename)
        properties["source_file_name"] = (normalize_value_for_storage(p.name), PropertyType.STRING)
        if p.suffix:
            properties["source_file_type"] = (normalize_value_for_storage(p.suffix.lstrip(".").lower()), PropertyType.STRING)
    return ParseResult(text=text, properties=properties)


def parse_csv_tsv(data: bytes, filename: str | None = None, delimiter: str = ",") -> ParseResult:
    """Parse CSV or TSV: concatenate cell text with newlines."""
    try:
        decoded = data.decode("utf-8")
    except UnicodeDecodeError:
        decoded = data.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(decoded), delimiter=delimiter)
    rows = list(reader)
    lines: list[str] = []
    for row in rows:
        lines.append(" ".join(cell.strip() for cell in row if cell.strip()))
    text = "\n".join(lines)
    properties: dict[str, tuple[str, PropertyType]] = {}
    if filename:
        p = Path(filename)
        properties["source_file_name"] = (normalize_value_for_storage(p.name), PropertyType.STRING)
        properties["source_file_type"] = (normalize_value_for_storage("csv" if delimiter == "," else "tsv"), PropertyType.STRING)
    return ParseResult(text=text, properties=properties)


def parse_txt(data: bytes, filename: str | None = None) -> ParseResult:
    """Plain text (.txt)."""
    return parse_text(data, filename)


def parse_md(data: bytes, filename: str | None = None) -> ParseResult:
    """Markdown (.md) - store as-is, no extra metadata."""
    return parse_text(data, filename)


def parse_csv(data: bytes, filename: str | None = None) -> ParseResult:
    """CSV."""
    return parse_csv_tsv(data, filename, delimiter=",")


def parse_tsv(data: bytes, filename: str | None = None) -> ParseResult:
    """TSV."""
    return parse_csv_tsv(data, filename, delimiter="\t")

"""Registry: select parser by extension/MIME and return normalized ParseResult."""

from collections.abc import Callable
from pathlib import Path

from relrag.infrastructure.document_parsers.base import ParseResult
from relrag.infrastructure.document_parsers.docx_parser import parse_docx
from relrag.infrastructure.document_parsers.epub_parser import parse_epub
from relrag.infrastructure.document_parsers.pdf_parser import parse_pdf
from relrag.infrastructure.document_parsers.pptx_parser import parse_pptx
from relrag.infrastructure.document_parsers.text_parser import (
    parse_csv,
    parse_md,
    parse_tsv,
    parse_txt,
)
from relrag.infrastructure.document_parsers.xlsx_parser import parse_xlsx

# extension (lower) -> parse function
_PARSERS_BY_EXT: dict[str, Callable[..., ParseResult]] = {
    "txt": parse_txt,
    "md": parse_md,
    "csv": parse_csv,
    "tsv": parse_tsv,
    "docx": parse_docx,
    "pdf": parse_pdf,
    "xlsx": parse_xlsx,
    "pptx": parse_pptx,
    "epub": parse_epub,
}

# MIME -> parse function (optional fallback)
_MIME_TO_EXT: dict[str, str] = {
    "text/plain": "txt",
    "text/markdown": "md",
    "text/csv": "csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/epub+zip": "epub",
}


def get_parser_for_filename(filename: str | None) -> Callable[..., ParseResult] | None:
    """Return parse function for given filename (by extension) or None."""
    if not filename:
        return None
    ext = Path(filename).suffix.lstrip(".").lower()
    return _PARSERS_BY_EXT.get(ext)


def get_parser_for_content_type(content_type: str | None) -> Callable[..., ParseResult] | None:
    """Return parse function for MIME type or None."""
    if not content_type:
        return None
    mime = content_type.split(";")[0].strip().lower()
    ext = _MIME_TO_EXT.get(mime)
    if not ext:
        return None
    return _PARSERS_BY_EXT.get(ext)


def parse_file(
    data: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> ParseResult:
    """
    Select parser by filename (extension) or content_type, run it, return ParseResult.
    Raises ValueError if no parser found or parse failed.
    """
    parser = get_parser_for_filename(filename) or get_parser_for_content_type(content_type)
    if not parser:
        ext = Path(filename).suffix if filename else content_type or "unknown"
        raise ValueError(f"No parser for file type: {ext}")
    return parser(data, filename)


def supported_extensions() -> list[str]:
    """Return list of supported file extensions (e.g. for frontend accept attribute)."""
    return sorted(_PARSERS_BY_EXT.keys())

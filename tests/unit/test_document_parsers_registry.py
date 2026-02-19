"""Unit tests for document_parsers.registry."""

import pytest

from relrag.infrastructure.document_parsers.base import ParseResult
from relrag.infrastructure.document_parsers.registry import (
    get_parser_for_content_type,
    get_parser_for_filename,
    parse_file,
    supported_extensions,
)


class TestGetParserForFilename:
    """Tests for get_parser_for_filename."""

    def test_none_returns_none(self) -> None:
        assert get_parser_for_filename(None) is None

    def test_txt_returns_parser(self) -> None:
        assert get_parser_for_filename("a.txt") is not None
        assert get_parser_for_filename("a.TXT") is not None

    def test_docx_pdf_xlsx_pptx_epub_return_parser(self) -> None:
        for ext in ("docx", "pdf", "xlsx", "pptx", "epub", "md", "csv", "tsv"):
            assert get_parser_for_filename(f"file.{ext}") is not None

    def test_unknown_extension_returns_none(self) -> None:
        assert get_parser_for_filename("file.xyz") is None
        assert get_parser_for_filename("file.unknown") is None


class TestGetParserForContentType:
    """Tests for get_parser_for_content_type."""

    def test_none_returns_none(self) -> None:
        assert get_parser_for_content_type(None) is None

    def test_text_plain_returns_parser(self) -> None:
        assert get_parser_for_content_type("text/plain") is not None

    def test_application_pdf_returns_parser(self) -> None:
        assert get_parser_for_content_type("application/pdf") is not None

    def test_content_type_with_charset(self) -> None:
        assert get_parser_for_content_type("text/plain; charset=utf-8") is not None

    def test_unknown_mime_returns_none(self) -> None:
        assert get_parser_for_content_type("application/octet-stream") is None


class TestParseFile:
    """Tests for parse_file."""

    def test_parse_txt_by_filename(self) -> None:
        data = b"Hello world"
        result = parse_file(data, filename="test.txt")
        assert isinstance(result, ParseResult)
        assert result.text == "Hello world"
        assert result.properties.get("source_file_name") == ("test.txt", result.properties["source_file_name"][1])
        assert result.properties.get("source_file_type") == ("txt", result.properties["source_file_type"][1])

    def test_parse_by_content_type_when_no_filename(self) -> None:
        data = b"a,b\n1,2"
        result = parse_file(data, filename=None, content_type="text/csv")
        assert result.text
        assert "1" in result.text and "2" in result.text

    def test_no_parser_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="No parser for file type"):
            parse_file(b"data", filename="file.xyz")
        with pytest.raises(ValueError, match="No parser for file type"):
            parse_file(b"data", filename=None, content_type="application/unknown")

    def test_unknown_extension_uses_content_type(self) -> None:
        # .bin unknown but content_type text/plain -> uses text parser
        result = parse_file(b"hello", filename="x.bin", content_type="text/plain")
        assert result.text == "hello"


class TestSupportedExtensions:
    """Tests for supported_extensions."""

    def test_returns_sorted_list(self) -> None:
        exts = supported_extensions()
        assert exts == sorted(exts)
        assert "txt" in exts
        assert "pdf" in exts
        assert "docx" in exts
        assert "epub" in exts

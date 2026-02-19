"""Unit tests for document_parsers.text_parser."""

import pytest

from relrag.domain.value_objects import PropertyType
from relrag.infrastructure.document_parsers.base import ParseResult
from relrag.infrastructure.document_parsers.text_parser import (
    parse_csv,
    parse_csv_tsv,
    parse_md,
    parse_text,
    parse_txt,
    parse_tsv,
)


class TestParseText:
    """Tests for parse_text."""

    def test_utf8_decode(self) -> None:
        result = parse_text(b"Hello \xd0\x9c\xd0\xb8\xd1\x80", filename=None)
        assert "Hello" in result.text
        assert result.properties == {}

    def test_with_filename_adds_properties(self) -> None:
        result = parse_text(b"content", filename="doc.txt")
        assert result.text == "content"
        assert result.properties["source_file_name"][0] == "doc.txt"
        assert result.properties["source_file_type"][0] == "txt"

    def test_filename_without_suffix_no_source_file_type(self) -> None:
        result = parse_text(b"x", filename="noext")
        assert "source_file_name" in result.properties
        assert result.properties["source_file_name"][0] == "noext"
        assert "source_file_type" not in result.properties

    def test_fallback_cp1251(self) -> None:
        # bytes that are invalid UTF-8 but valid cp1251 (e.g. 0xd0 = 'Р' in cp1251)
        result = parse_text(b"\xd0\xe0\xe7", filename=None)
        assert result.text  # decoded somehow

    def test_replace_on_decode_error(self) -> None:
        # invalid UTF-8 and invalid cp1251 -> replace
        result = parse_text(b"\xff\xfe\xfd", filename=None)
        assert result.text  # replacement chars

    def test_utf8_fails_cp1251_fails_uses_replace(self) -> None:
        # Bytes invalid for both UTF-8 and cp1251 (e.g. 0x98 0x99 in cp1251 are invalid)
        result = parse_text(b"\x98\x99\x9a", filename=None)
        assert result.text  # replacement chars


class TestParseTxtAndMd:
    """Tests for parse_txt and parse_md."""

    def test_parse_txt(self) -> None:
        result = parse_txt(b"plain text", filename="a.txt")
        assert result.text == "plain text"
        assert result.properties["source_file_type"][0] == "txt"

    def test_parse_md(self) -> None:
        result = parse_md(b"# Title\n\nbody", filename="readme.md")
        assert "# Title" in result.text
        assert result.properties["source_file_type"][0] == "md"


class TestParseCsvTsv:
    """Tests for parse_csv_tsv, parse_csv, parse_tsv."""

    def test_parse_csv_simple(self) -> None:
        data = b"a,b,c\n1,2,3"
        result = parse_csv(data, filename="data.csv")
        assert "a b c" in result.text or "1 2 3" in result.text
        assert result.properties["source_file_name"][0] == "data.csv"
        assert result.properties["source_file_type"][0] == "csv"

    def test_parse_tsv(self) -> None:
        data = b"x\ty\n1\t2"
        result = parse_tsv(data, filename="t.tsv")
        assert result.properties["source_file_type"][0] == "tsv"
        assert "x" in result.text and "y" in result.text

    def test_parse_csv_tsv_empty_cells(self) -> None:
        data = b"a,,b\n,2,"
        result = parse_csv_tsv(data, delimiter=",")
        assert result.text
        assert result.properties == {}

    def test_parse_csv_tsv_utf8_replace(self) -> None:
        data = b"a,b\n\xff\xfe,c"
        result = parse_csv_tsv(data)
        assert len(result.text) > 0

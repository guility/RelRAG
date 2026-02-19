"""Unit tests for document_parsers.metadata_keys."""

import pytest

from relrag.domain.value_objects import PropertyType
from relrag.infrastructure.document_parsers.metadata_keys import (
    CANONICAL_KEYS,
    PARSER_KEY_TO_CANONICAL,
    normalize_value_for_storage,
)


class TestNormalizeValueForStorage:
    """Tests for normalize_value_for_storage."""

    def test_none_returns_empty_string(self) -> None:
        assert normalize_value_for_storage(None) == ""

    def test_bool_true(self) -> None:
        assert normalize_value_for_storage(True) == "true"

    def test_bool_false(self) -> None:
        assert normalize_value_for_storage(False) == "false"

    def test_int(self) -> None:
        assert normalize_value_for_storage(42) == "42"
        assert normalize_value_for_storage(0) == "0"

    def test_float(self) -> None:
        assert normalize_value_for_storage(3.14) == "3.14"

    def test_string_passthrough(self) -> None:
        assert normalize_value_for_storage("hello") == "hello"
        assert normalize_value_for_storage("") == ""


class TestConstants:
    """Tests for module constants."""

    def test_canonical_keys_contains_expected(self) -> None:
        assert "title" in CANONICAL_KEYS
        assert "author" in CANONICAL_KEYS
        assert "source_file_name" in CANONICAL_KEYS
        assert CANONICAL_KEYS["title"] == PropertyType.STRING
        assert CANONICAL_KEYS["page_count"] == PropertyType.INT
        assert CANONICAL_KEYS["created_date"] == PropertyType.DATE

    def test_parser_key_to_canonical_mappings(self) -> None:
        assert PARSER_KEY_TO_CANONICAL["title"] == ("title", PropertyType.STRING)
        assert PARSER_KEY_TO_CANONICAL["created"] == ("created_date", PropertyType.DATE)
        assert PARSER_KEY_TO_CANONICAL["/Title"] == ("title", PropertyType.STRING)
        assert PARSER_KEY_TO_CANONICAL["dc:creator"] == ("author", PropertyType.STRING)

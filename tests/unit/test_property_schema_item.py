"""Unit tests for PropertySchemaItem (property_repository port)."""

from relrag.application.ports.repositories.property_repository import (
    PropertySchemaItem,
)
from relrag.domain.value_objects import PropertyType


def test_property_schema_item_creation() -> None:
    """PropertySchemaItem stores key, type and optional values."""
    item = PropertySchemaItem(key="status", property_type=PropertyType.STRING, values=["a", "b"])
    assert item.key == "status"
    assert item.property_type == PropertyType.STRING
    assert item.values == ["a", "b"]


def test_property_schema_item_values_default_empty() -> None:
    """When values is None, .values is empty list."""
    item = PropertySchemaItem(key="x", property_type=PropertyType.INT, values=None)
    assert item.values == []

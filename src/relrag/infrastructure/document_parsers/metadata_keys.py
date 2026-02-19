"""Canonical metadata keys for document properties (unified across file formats)."""

from relrag.domain.value_objects import PropertyType

# Canonical keys used in Properties; parsers map format-specific keys to these.
CANONICAL_KEYS = {
    "title": PropertyType.STRING,
    "author": PropertyType.STRING,
    "created_date": PropertyType.DATE,
    "modified_date": PropertyType.DATE,
    "page_count": PropertyType.INT,
    "language": PropertyType.STRING,
    "source_file_name": PropertyType.STRING,
    "source_file_type": PropertyType.STRING,
}

# Parser-specific key -> (canonical_key, property_type)
PARSER_KEY_TO_CANONICAL: dict[str, tuple[str, PropertyType]] = {
    # docx / OOXML
    "title": ("title", PropertyType.STRING),
    "subject": ("title", PropertyType.STRING),
    "author": ("author", PropertyType.STRING),
    "creator": ("author", PropertyType.STRING),
    "created": ("created_date", PropertyType.DATE),
    "modified": ("modified_date", PropertyType.DATE),
    "lastModifiedBy": ("author", PropertyType.STRING),
    "pages": ("page_count", PropertyType.INT),
    "language": ("language", PropertyType.STRING),
    # pdf
    "/Title": ("title", PropertyType.STRING),
    "Title": ("title", PropertyType.STRING),
    "/Author": ("author", PropertyType.STRING),
    "Author": ("author", PropertyType.STRING),
    "/CreationDate": ("created_date", PropertyType.DATE),
    "CreationDate": ("created_date", PropertyType.DATE),
    "/ModDate": ("modified_date", PropertyType.DATE),
    "ModDate": ("modified_date", PropertyType.DATE),
    "/Producer": ("author", PropertyType.STRING),
    "/Lang": ("language", PropertyType.STRING),
    # epub
    "dc:title": ("title", PropertyType.STRING),
    "dc:creator": ("author", PropertyType.STRING),
    "dc:language": ("language", PropertyType.STRING),
    "dc:date": ("created_date", PropertyType.DATE),
}


def normalize_value_for_storage(value: str | int | float | bool | None) -> str:
    """Convert a value to string for property.value storage."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)

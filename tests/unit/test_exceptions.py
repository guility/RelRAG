"""Unit tests for domain exceptions."""

import pytest

from relrag.domain.exceptions import (
    DuplicateDocument,
    NotFound,
    PermissionDenied,
    RelRAGError,
    ValidationError,
)


def test_permission_denied_inherits_relrag_error() -> None:
    """PermissionDenied is a subclass of RelRAGError."""
    assert issubclass(PermissionDenied, RelRAGError)


def test_not_found_inherits_relrag_error() -> None:
    """NotFound is a subclass of RelRAGError."""
    assert issubclass(NotFound, RelRAGError)


def test_duplicate_document_inherits_relrag_error() -> None:
    """DuplicateDocument is a subclass of RelRAGError."""
    assert issubclass(DuplicateDocument, RelRAGError)


def test_validation_error_inherits_relrag_error() -> None:
    """ValidationError is a subclass of RelRAGError."""
    assert issubclass(ValidationError, RelRAGError)


def test_raise_permission_denied_catchable_as_relrag_error() -> None:
    """PermissionDenied can be caught as RelRAGError."""
    with pytest.raises(RelRAGError):
        raise PermissionDenied("no access")


def test_raise_not_found_catchable_as_relrag_error() -> None:
    """NotFound can be caught as RelRAGError."""
    with pytest.raises(RelRAGError):
        raise NotFound("Document", "123")


def test_exception_message_preserved() -> None:
    """Exception message is preserved when raised."""
    msg = "User does not have write access"
    with pytest.raises(PermissionDenied, match=msg):
        raise PermissionDenied(msg)

"""Domain exceptions."""


class RelRAGError(Exception):
    """Base exception for RelRAG."""

    pass


class PermissionDenied(RelRAGError):
    """User does not have permission for the requested action."""

    pass


class NotFound(RelRAGError):
    """Requested resource was not found."""

    pass


class DuplicateDocument(RelRAGError):
    """Document with same source hash already exists."""

    pass


class ValidationError(RelRAGError):
    """Validation failed for input data."""

    pass

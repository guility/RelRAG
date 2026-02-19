"""Permission actions for RBAC."""

from enum import StrEnum


class PermissionAction(StrEnum):
    """Actions that can be performed on collections."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    MIGRATE = "migrate"

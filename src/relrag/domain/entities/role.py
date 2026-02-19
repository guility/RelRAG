"""Role entity for RBAC."""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class Role:
    """Role - viewer, editor, admin with associated actions."""

    id: UUID
    name: str
    description: str

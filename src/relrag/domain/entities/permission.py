"""Permission entity - user access to collection."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Permission:
    """Permission - user (subject) has role on collection, optional actions override."""

    id: UUID
    collection_id: UUID
    subject: str
    role_id: UUID
    created_at: datetime
    created_by: str | None = None
    actions_override: list[str] | None = None

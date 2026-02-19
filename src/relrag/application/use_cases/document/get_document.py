"""Get document use case."""

from uuid import UUID

from relrag.application.dto.document_dto import DocumentOutput
from relrag.application.ports import PermissionChecker
from relrag.domain.exceptions import NotFound, PermissionDenied
from relrag.domain.value_objects import PermissionAction


class GetDocumentUseCase:
    """Get document by id within collection context."""

    def __init__(
        self,
        unit_of_work_factory: type,
        permission_checker: PermissionChecker,
    ) -> None:
        self._uow_factory = unit_of_work_factory
        self._permission_checker = permission_checker

    async def execute(self, user_id: str, document_id: UUID, collection_id: UUID) -> DocumentOutput:
        """Get document by id."""
        has_read = await self._permission_checker.check(
            user_id, collection_id, PermissionAction.READ
        )
        if not has_read:
            raise PermissionDenied("User does not have read access to collection")

        async with self._uow_factory() as uow:
            document = await uow.documents.get_by_id(document_id)
            if not document or document.deleted_at:
                raise NotFound("Document", str(document_id))

            pack = await uow.packs.list(
                document_id=document_id,
                collection_id=collection_id,
                limit=1,
            )
            if not pack[0]:
                raise NotFound("Document", str(document_id))

            return DocumentOutput(
                id=document.id,
                content=document.content,
                source_hash=document.source_hash,
                created_at=document.created_at,
                updated_at=document.updated_at,
                deleted_at=document.deleted_at,
            )

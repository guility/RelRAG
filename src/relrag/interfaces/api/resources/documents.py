"""Document API resources."""

from uuid import UUID

import falcon.asgi

from relrag.application.dto.document_dto import DocumentCreateInput, DocumentOutput
from relrag.application.use_cases.document.get_document import GetDocumentUseCase
from relrag.application.use_cases.document.load_document import LoadDocumentUseCase
from relrag.domain.exceptions import NotFound, PermissionDenied, ValidationError


class DocumentsResource:
    """POST /v1/documents - create document."""

    def __init__(self, load_document: LoadDocumentUseCase) -> None:
        self._load_document = load_document

    async def on_post(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        """Create document in collection."""
        user = getattr(req.context, "user", None)
        if not user:
            resp.status = falcon.HTTP_401
            resp.media = {"error": "Unauthorized"}
            return

        try:
            body = await req.get_media()
            collection_id = UUID(body["collection_id"])
            content = body["content"]
            properties = {k: (v["value"], v["type"]) for k, v in body.get("properties", {}).items()}
        except (KeyError, ValueError) as e:
            resp.status = falcon.HTTP_400
            resp.media = {"error": str(e)}
            return

        try:
            result = await self._load_document.execute(
                user.user_id,
                DocumentCreateInput(
                    collection_id=collection_id,
                    content=content,
                    properties=properties,
                ),
            )
            resp.media = _document_to_dict(result)
            resp.status = falcon.HTTP_201
        except PermissionDenied:
            resp.status = falcon.HTTP_403
            resp.media = {"error": "Permission denied"}
        except ValidationError as e:
            resp.status = falcon.HTTP_400
            resp.media = {"error": str(e)}


class DocumentResource:
    """GET /v1/documents/{id} - get document (requires collection_id query param)."""

    def __init__(self, get_document: GetDocumentUseCase) -> None:
        self._get_document = get_document

    async def on_get(
        self,
        req: falcon.asgi.Request,
        resp: falcon.asgi.Response,
        document_id: str,
    ) -> None:
        """Get document by id."""
        user = getattr(req.context, "user", None)
        if not user:
            resp.status = falcon.HTTP_401
            resp.media = {"error": "Unauthorized"}
            return

        collection_id_str = req.get_param("collection_id")
        if not collection_id_str:
            resp.status = falcon.HTTP_400
            resp.media = {"error": "collection_id query parameter required"}
            return

        try:
            doc_id = UUID(document_id)
            coll_id = UUID(collection_id_str)
        except ValueError:
            resp.status = falcon.HTTP_400
            resp.media = {"error": "Invalid UUID"}
            return

        try:
            result = await self._get_document.execute(user.user_id, doc_id, coll_id)
            resp.media = _document_to_dict(result)
            resp.status = falcon.HTTP_200
        except NotFound:
            resp.status = falcon.HTTP_404
            resp.media = {"error": "Document not found"}
        except PermissionDenied:
            resp.status = falcon.HTTP_403
            resp.media = {"error": "Permission denied"}


def _document_to_dict(d: DocumentOutput) -> dict:
    return {
        "id": str(d.id),
        "content": d.content,
        "source_hash": d.source_hash.hex(),
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
        "deleted_at": d.deleted_at.isoformat() if d.deleted_at else None,
    }
